#!/usr/bin/env python3
"""Adversarial, model-free checks of FIXCHECK decisions and launch guards."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import thresholds as t
import fixcheck as f


def fixture():
    units = [{"id": f"{k}{i}", "klass": k, "type": "design" if k == "C" and i < 2 else None,
              "sessions": 2 if k == "B" else 1, "sha256": f"{k}{i}"} for k in "ABC" for i in range(4)]
    manifest = {"units": units, "runtime": {"arms": {"O": {"commit": "candidate"}},
                "files": {"h1_run.py": "runner"}, "units": {k: k for k in "ABC"},
                "launch": {"cells": {c: {"model": c} for c in t.CELLS}}}}
    for u in units:
        u["functions"] = ["test_recall_0" if u["klass"] == "B" and i == 0 else f"test_{i}" for i in range(10)]
        u["items"] = {fn: [fn] for fn in u["functions"]}
    old, new, events = [], [], {"manifest_sha256": "manifest", "rows": []}
    for cell in t.CELLS:
        for u in units:
            grade = {"error": "", "functions": {fn: True for fn in u["functions"]},
                     "items": {fn: True for fn in u["functions"]}, "n": 10, "passed": 10,
                     "recall": True if u["klass"] == "B" else None, "suite_regression": False}
            row = {"cell": cell, "unit": u["id"], "arm": "O", "klass": u["klass"], "type": u["type"],
                   "score": 1., "tokens_total": 100, "grade": grade}
            for arm in ("O", "N1", "N2"):
                old.append(dict(copy.deepcopy(row), arm=arm))
            row.update(tag="fixcheck", arm_commit="candidate", runner_sha256="runner",
                       units_sha256=u["klass"], unit_sha256=u["sha256"], model_asked=cell,
                       freeze_sha256="", cap=17_000_000, cap_decision="D45",
                       sessions=[{"tokens_total": 100 // u["sessions"]} for _ in range(u["sessions"])])
            new.append(row)
            events["rows"].append({"cell": cell, "unit": u["id"], "row_sha256": t.row_sha(row),
                                  **{m: {"status": "observed", "evidence": [
                                      {"sha256": "a"*64, "locator": "synthetic:1", "summary": "test fixture"}]}
                                     for m in ("M1", "M2", "M3", "R1", "R2")}})
    return manifest, {"rows": old}, new, events


class ThresholdTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.baseline, self.rows, self.events = fixture()

    def evaluate(self):
        return t.evaluate(self.manifest, self.baseline, self.rows, self.events, "manifest")

    def event(self, row):
        return next(e for e in self.events["rows"] if (e["cell"], e["unit"]) == (row["cell"], row["unit"]))

    def bind(self, row):
        self.event(row)["row_sha256"] = t.row_sha(row)

    def row(self, unit, cell="codex"):
        return next(r for r in self.rows if r["unit"] == unit and r["cell"] == cell)

    def change_score(self, row, lost):
        row["grade"]["items"] = {f"test_{i}": i >= lost for i in range(10)}
        row["grade"]["functions"] = dict(row["grade"]["items"])
        row["grade"]["passed"] = 10-lost
        row["score"] = (10-lost)/10
        self.bind(row)

    def change_tokens(self, row, amount):
        row["tokens_total"] = amount
        row["sessions"][0]["tokens_total"] = amount
        self.bind(row)

    def test_complete_pass_and_no_false_cost_claim(self):
        out = self.evaluate()
        self.assertEqual(out["numeric_outcome"], "pass")
        self.assertEqual(out["counted_rows"], 24)
        self.assertTrue(any("no measured" in a for a in out["actions"]))

    def test_exact_tenth_is_allowed_and_still_reported(self):
        self.change_score(self.row("C0"), 1)
        out = self.evaluate()
        self.assertEqual(out["numeric_outcome"], "pass")
        self.assertEqual(out["drops"][0]["lost_hidden"]["functions"], ["test_0"])

    def test_more_than_tenth_design_reverts_r2(self):
        self.change_score(self.row("C0"), 2)
        self.assertIn("revert R2", self.evaluate()["actions"])

    def test_non_design_large_drop_has_no_invented_revert(self):
        self.change_score(self.row("C3"), 2)
        out = self.evaluate()
        self.assertIn("block release; owner disposition for non-design C", out["actions"])
        self.assertNotIn("revert R2", out["actions"])

    def test_small_token_threshold_inclusive(self):
        self.change_tokens(self.row("A0"), 120)
        self.assertEqual(self.evaluate()["numeric_outcome"], "pass")
        self.change_tokens(self.row("A0"), 121)
        self.assertIn("revert M1+M2+R2", self.evaluate()["actions"])

    def test_one_small_failure_not_hidden_by_other_savings(self):
        self.change_tokens(self.row("A0"), 200)
        for u in ("A1", "A2", "A3"):
            self.change_tokens(self.row(u), 1)
        self.assertEqual(self.evaluate()["numeric_outcome"], "fail")

    def test_small_score_drop_fails(self):
        self.change_score(self.row("A0"), 1)
        self.assertEqual(self.evaluate()["numeric_outcome"], "fail")

    def test_recall_cannot_swap_remembered_tasks(self):
        for r in self.baseline["rows"]:
            if r["unit"] == "B1" and r["arm"] == "O" and r["cell"] == "codex":
                r["grade"]["recall"] = False
                r["grade"]["functions"]["test_recall_0"] = False
                r["grade"]["items"]["test_recall_0"] = False
                r["grade"]["passed"] = 9
                r["score"] = .9
        row = self.row("B0")
        row["grade"]["recall"] = False
        row["grade"]["functions"]["test_recall_0"] = False
        row["grade"]["items"]["test_recall_0"] = False
        row["grade"]["passed"] = 9
        row["score"] = .9
        self.bind(row)
        out = self.evaluate()
        mem = next(x for x in out["memory"] if x["cell"] == "codex")
        self.assertEqual(mem["new_remembered"], mem["old_remembered"])
        self.assertFalse(mem["passed"])
        self.assertIn("revert M1+M2", out["actions"])

    def test_m1_three_passes_two_fails_unknown_incomplete(self):
        self.event(self.row("B0"))["M1"]["status"] = "absent"
        self.assertEqual(self.evaluate()["numeric_outcome"], "pass")
        self.event(self.row("B1"))["M1"]["status"] = "absent"
        self.assertEqual(self.evaluate()["numeric_outcome"], "fail")
        self.event(self.row("B1"))["M1"]["status"] = "unverified"
        self.assertEqual(self.evaluate()["numeric_outcome"], "incomplete")

    def test_m2_not_triggered_is_not_a_pass(self):
        self.event(self.row("B0"))["M2"]["status"] = "unverified"
        out = self.evaluate()
        self.assertEqual(out["numeric_outcome"], "pass")
        self.assertEqual(out["mechanisms_unverified"][0]["fix"], "M2")

    def test_m3_and_r1_defects_block_release_even_if_scores_pass(self):
        self.event(self.row("B0"))["M3"]["status"] = "absent"
        self.event(self.row("C0"))["R1"]["status"] = "absent"
        out = self.evaluate()
        self.assertEqual(out["numeric_outcome"], "pass")
        self.assertEqual(sum(a.startswith("block release") for a in out["actions"]), 2)

    def test_duplicate_rows_rejected(self):
        self.rows.append(copy.deepcopy(self.rows[0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.evaluate()

    def test_missing_row_incomplete_not_zero(self):
        row = self.rows.pop()
        event = self.event(row)
        event["row_sha256"] = None
        for m in ("M1", "M2", "M3", "R1", "R2"):
            event[m]["status"] = "unverified"
        self.assertEqual(self.evaluate()["numeric_outcome"], "incomplete")

    def test_row_provenance_mismatch_rejected(self):
        self.rows[0]["runner_sha256"] = "other"
        self.bind(self.rows[0])
        with self.assertRaisesRegex(ValueError, "runner_sha256"):
            self.evaluate()

    def test_audit_stale_row_rejected(self):
        self.rows[0]["tokens_total"] = 110
        with self.assertRaisesRegex(ValueError, "digest"):
            self.evaluate()

    def test_observation_without_evidence_rejected(self):
        self.events["rows"][0]["R1"]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "evidence"):
            self.evaluate()

    def test_unknown_unit_rejected(self):
        self.rows[0]["unit"] = "extra"
        with self.assertRaisesRegex(ValueError, "unknown"):
            self.evaluate()

    def test_changed_hidden_function_set_rejected(self):
        self.rows[0]["grade"]["functions"].pop("test_0")
        self.bind(self.rows[0])
        with self.assertRaisesRegex(ValueError, "hidden functions"):
            self.evaluate()

    def test_grade_arithmetic_tampering_rejected(self):
        self.rows[0]["grade"]["passed"] = 9
        with self.assertRaisesRegex(ValueError, "counts"):
            self.evaluate()

    def test_false_function_cannot_leave_item_true(self):
        row = self.row("A0")
        row["grade"]["functions"]["test_0"] = False
        self.bind(row)
        with self.assertRaisesRegex(ValueError, "mapping"):
            self.evaluate()

    def test_forged_recall_cannot_hide_forgetting(self):
        row = self.row("B0")
        row["grade"]["functions"] = {k: False for k in row["grade"]["functions"]}
        row["grade"]["items"] = {k: False for k in row["grade"]["items"]}
        row["grade"]["passed"] = 0
        row["score"] = 0.
        self.bind(row)
        with self.assertRaisesRegex(ValueError, "recall disagrees"):
            self.evaluate()

    def test_negative_session_usage_cannot_cancel(self):
        row = self.row("B0")
        row["sessions"] = [{"tokens_total": -100}, {"tokens_total": 200}]
        self.bind(row)
        with self.assertRaisesRegex(ValueError, "positive integers"):
            self.evaluate()

    def test_wrong_budget_rejected(self):
        row = self.row("A0", "claude")
        row["cap"] = 30_000_000
        self.bind(row)
        with self.assertRaisesRegex(ValueError, "budget"):
            self.evaluate()

    def test_session_usage_mismatch_rejected(self):
        self.rows[0]["sessions"][0]["tokens_total"] = 1
        self.bind(self.rows[0])
        with self.assertRaisesRegex(ValueError, "usage"):
            self.evaluate()


class LaunchGuardTests(unittest.TestCase):
    def test_started_even_if_only_start_ledger_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state/"starts-fixcheck-codex.jsonl").write_text('{"event":"start"}\n')
            self.assertTrue(f.has_started(state))

    def test_cannot_prepare_same_state(self):
        runner = type("R", (), {"STATE": "/tmp/same"})()
        with patch.object(f, "candidate"):
            with self.assertRaisesRegex(ValueError, "separate"):
                f.prepare(runner, {}, Path("/tmp/same"))

    def test_cannot_prepare_existing_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = type("R", (), {"STATE": tmp})()
            with patch.object(f, "candidate"):
                with self.assertRaisesRegex(ValueError, "already exists"):
                    f.prepare(runner, {}, Path("/different"))

    def test_cannot_refreeze_started_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state/"starts-fixcheck-codex.jsonl").write_text('{}\n')
            runner = type("R", (), {"STATE": tmp})()
            with self.assertRaisesRegex(ValueError, "cannot rewrite"):
                f.freeze_manifest(runner, {})


if __name__ == "__main__":
    unittest.main()
