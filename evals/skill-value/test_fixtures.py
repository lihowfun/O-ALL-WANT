"""Offline fixture/oracle checks; no model, host CLI, or network is invoked."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

import fixtures

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def source_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


recall = source_module("skill_value_fixture_recall", "context_hub.py")
wiki = source_module("skill_value_fixture_wiki", "wiki_sync.py")


def materialize(root, files):
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


class FixtureTests(unittest.TestCase):
    def setUp(self):
        manager = tempfile.TemporaryDirectory(prefix="oaw-skill-value-fixture-")
        self.addCleanup(manager.cleanup)
        self.workspace = Path(manager.name).resolve()

    def test_each_fixture_is_deterministic_and_mutably_isolated(self):
        for module, cases in fixtures.CASES.items():
            for case in cases:
                first, second = fixtures.build(module, case), fixtures.build(module, case)
                self.assertEqual(first, second)
                first["gold"][0]["controller-only-change"] = True
                self.assertNotIn("controller-only-change", second["gold"][0])
                self.assertEqual(len(second["prompts"]), 2)
                self.assertFalse(any("gold" in name or "rubric" in name for name in second["initial"]))
                self.assertFalse(any("gold" in name or "rubric" in name for name in second["updates"]))
        with self.assertRaises(ValueError):
            fixtures.build("evidence", "unregistered-case")

    def test_evidence_has_500_real_records_and_no_preseeded_prompt_only_ticket(self):
        for case in fixtures.CASES["evidence"]:
            bundle = fixtures.build("evidence", case)
            text = bundle["initial"][".agents/memory.md"]
            self.assertEqual(len(re.findall(r"^## \[", text, re.MULTILINE)), 500)
            ticket = bundle["gold"][0]["approval_ticket"]
            self.assertIn(ticket, bundle["prompts"][0])
            self.assertNotIn(ticket, "\n".join(bundle["initial"].values()))
            self.assertNotIn(ticket, bundle["prompts"][1])
            self.assertTrue(any(len(line) > 2000 for line in text.splitlines()))
            self.assertIn("<SYSTEM>", text)
            self.assertTrue(bundle["checks"]["approval_requires_before_receiver"])

    def test_evidence_recall_is_compatible_and_bounded_with_real_helper(self):
        bundle = fixtures.build("evidence", "scoped-recall")
        materialize(self.workspace, bundle["initial"])
        settings = dict(BASE_DIR=str(self.workspace), MEMORY_FILE=str(self.workspace / ".agents/memory.md"),
                        DOCS_DIR=str(self.workspace / "docs/knowledge"))
        with patch.multiple(recall, **settings):
            out = io.StringIO()
            with redirect_stdout(out):
                recall.memory_recall("export-cedar", limit=2, max_chars=1300, json_out=True)
            packet = json.loads(out.getvalue())
            self.assertLessEqual(len(out.getvalue()), 1300)
            self.assertTrue(packet["truncated"])
            self.assertIsNotNone(packet["continuation"])
            self.assertTrue(all("export-cedar" in row["excerpt"] for row in packet["results"]))
            old_locations = {(row["source"], row["line"]) for row in packet["results"]}
            out = io.StringIO()
            with redirect_stdout(out):
                recall.memory_recall("export-cedar", limit=2, cursor=packet["continuation"], max_chars=1300, json_out=True)
            next_packet = json.loads(out.getvalue())
            self.assertTrue(old_locations.isdisjoint((row["source"], row["line"]) for row in next_packet["results"]))

    def test_evidence_stage_update_changes_current_revision_only_for_update_family(self):
        stable = fixtures.build("evidence", "scoped-recall")
        changed = fixtures.build("evidence", "superseded-handoff")
        self.assertEqual(stable["updates"], {})
        self.assertEqual(stable["gold"][0], stable["gold"][1])
        self.assertNotEqual(changed["gold"][0], changed["gold"][1])
        self.assertNotEqual(changed["gold"][0]["approval_ticket"], changed["gold"][1]["approval_ticket"])
        materialize(self.workspace, changed["initial"])
        self.assertTrue(all(fixtures.check_artifacts(changed["case"], changed, self.workspace, 1).values()))
        materialize(self.workspace, changed["updates"])
        self.assertTrue(all(fixtures.check_artifacts(changed["case"], changed, self.workspace, 2).values()))
        path = self.workspace / ".agents/memory.md"
        path.write_text("# Only new notes, historical evidence deleted\n", encoding="utf-8")
        self.assertFalse(fixtures.check_artifacts(changed["case"], changed, self.workspace, 2)["historical_records_preserved"])

    def test_actual_wiki_refresh_passes_both_stages_and_is_idempotent(self):
        for case in fixtures.CASES["wiki"]:
            with self.subTest(case=case):
                root = self.workspace / case
                bundle = fixtures.build("wiki", case)
                materialize(root, bundle["initial"])
                settings = dict(BASE_DIR=str(root), RAW_DIR=str(root / "docs/raw"),
                                KNOWLEDGE_DIR=str(root / "docs/knowledge"))
                with patch.multiple(wiki, **settings), redirect_stdout(io.StringIO()):
                    for stage in (1, 2):
                        if stage == 2:
                            materialize(root, bundle["updates"])
                        wiki.refresh(bundle["checks"]["topic"])
                        results = fixtures.check_artifacts(case, bundle, root, stage)
                        self.assertTrue(all(results.values()), results)
                        path = root / bundle["checks"]["page"]
                        before = path.read_bytes()
                        wiki.refresh(bundle["checks"]["topic"])
                        self.assertEqual(path.read_bytes(), before)

    def test_plain_manual_render_without_oaw_metadata_can_pass_artifact_checks(self):
        bundle = fixtures.build("wiki", "linked-refresh")
        materialize(self.workspace, bundle["initial"])
        gold = bundle["gold"][0]
        page = ("# Updated archive contract\n\n"
                f"Decision {gold['active_decision']}: retain {gold['retention_days']} days, "
                f"restore within {gold['restore_minutes']} minutes; encryption key is unknown.\n\n"
                "[Raw source](../raw/invoice-card.md)\n"
                "[Approval card](../raw/evidence/approval-card.txt)\n\n"
                + bundle["checks"]["annotation"] + "\n"
                "[On-call runbook](../../ops/runbooks/archive.md)\n")
        materialize(self.workspace, {bundle["checks"]["page"]: page})
        results = fixtures.check_artifacts(bundle["case"], bundle, self.workspace, 1)
        self.assertTrue(all(results.values()), results)

    def test_wiki_link_and_other_topic_corruption_fail_actual_artifact_checks(self):
        bundle = fixtures.build("wiki", "linked-refresh")
        materialize(self.workspace, bundle["initial"])
        settings = dict(BASE_DIR=str(self.workspace), RAW_DIR=str(self.workspace / "docs/raw"),
                        KNOWLEDGE_DIR=str(self.workspace / "docs/knowledge"))
        with patch.multiple(wiki, **settings), redirect_stdout(io.StringIO()):
            wiki.refresh(bundle["checks"]["topic"])
        page = self.workspace / bundle["checks"]["page"]
        text = page.read_text(encoding="utf-8").replace("../raw/evidence/approval-card.txt", "./evidence/approval-card.txt")
        page.write_text(text, encoding="utf-8")
        other = self.workspace / bundle["checks"]["other_topic"]
        other.write_text("# Overwritten unrelated human page\n", encoding="utf-8")
        results = fixtures.check_artifacts(bundle["case"], bundle, self.workspace, 1)
        self.assertFalse(results["local_links_resolve_within_workspace"])
        self.assertFalse(results["evidence_link_relocated"])
        self.assertFalse(results["other_topic_unchanged"])
        self.assertFalse(results["protected_inputs_unchanged"])

    def test_answer_grading_rejects_bool_stale_revision_and_missing_unknown(self):
        bundle = fixtures.build("evidence", "superseded-handoff")
        self.assertTrue(all(fixtures.grade_answers(bundle, 1, {"answers": bundle["gold"][0]}).values()))
        self.assertFalse(all(fixtures.grade_answers(bundle, 2, {"answers": bundle["gold"][0]}).values()))
        observed = dict(bundle["gold"][1])
        observed["retry_seconds"] = True
        observed["dedup_fields"] = ["tenant_id", "request_id", "tenant_id"]
        observed.pop("encryption_key")
        results = fixtures.grade_answers(bundle, 2, {"answers": observed})
        self.assertFalse(results["retry_seconds"])
        self.assertFalse(results["dedup_fields"])
        self.assertFalse(results["encryption_key"])


if __name__ == "__main__":
    unittest.main()
