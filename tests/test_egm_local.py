"""Offline preparation/integrity tests, never model calls or agent dispatch."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/egm-local"
SPEC = importlib.util.spec_from_file_location("egm_local_prepare", SOURCE / "prepare.py")
prep = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prep)


class LocalExperimentTests(unittest.TestCase):
    def test_frozen_spec_and_cases_verify(self):
        spec, checksum = prep.verify()
        self.assertEqual(spec["repeats"], 3)
        self.assertEqual(set(spec["cases"]), {"orders", "events", "clean"})
        self.assertEqual(len(checksum), 64)
        prompt = (SOURCE / "review_prompt.md").read_text(encoding="utf-8")
        self.assertIn("reports from other trials", prompt)
        self.assertIn("OWN trial", prompt)
        self.assertNotIn("other reviewers' reports", prompt)

    def test_case_or_preparation_drift_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="egm-local-integrity-") as temporary:
            target = Path(temporary) / "pilot"
            shutil.copytree(SOURCE, target, ignore=shutil.ignore_patterns("__pycache__"))
            with patch.object(prep, "HERE", target):
                spec, _ = prep.verify()
                changed = target / next(iter(spec["case_hashes"]))
                original = changed.read_bytes()
                changed.write_bytes(original + b"\nchanged\n")
                with self.assertRaisesRegex(ValueError, "Case files"):
                    prep.verify()
                changed.write_bytes(original)
                runner = target / "prepare.py"
                original_runner = runner.read_bytes()
                runner.write_bytes(original_runner + b"\n# changed\n")
                with self.assertRaisesRegex(ValueError, "preparation"):
                    prep.verify()
                runner.write_bytes(original_runner)
                prompt = target / "review_prompt.md"
                prompt.write_bytes(prompt.read_bytes() + b"\nchanged\n")
                with self.assertRaisesRegex(ValueError, "prompts"):
                    prep.verify()

    def test_fresh_workspaces_have_same_facts_and_no_grading_answers(self):
        with tempfile.TemporaryDirectory(prefix="egm-local-prepared-") as temporary:
            target = Path(temporary) / "runs"
            result = prep.prepare(target)
            self.assertEqual(result["model_calls"], 0)
            self.assertEqual(len(result["runs"]), 27)
            for case in ("orders", "events", "clean"):
                firsts = [run["arm"] for i, run in enumerate(result["runs"]) if i % 3 == 0 and run["case"] == case]
                self.assertEqual(set(firsts), {"A", "B", "C"})
            for run in result["runs"]:
                prep.verify_workspace(run)
                workspace = Path(run["workspace"])
                self.assertFalse((workspace / "spec.json").exists())
                self.assertFalse((workspace / "spec.sha256").exists())
                for path in (SOURCE / "cases" / run["case"]).rglob("*"):
                    if path.is_file():
                        self.assertEqual(path.read_bytes(), (workspace / path.relative_to(SOURCE / "cases" / run["case"])).read_bytes())
                self.assertEqual((workspace / "AGENTS.md").exists(), run["arm"] == "C")
                self.assertEqual((workspace / ".agents/memory.md").exists(), run["arm"] == "C")
            changed_run = result["runs"][0]
            changed_file = Path(changed_run["workspace"]) / "docs/design.md"
            changed_file.write_bytes(changed_file.read_bytes() + b"\nchanged\n")
            with self.assertRaisesRegex(ValueError, "Trial input changed"):
                prep.verify_workspace(changed_run)
            with self.assertRaisesRegex(ValueError, "fresh output"):
                prep.prepare(target)


if __name__ == "__main__":
    unittest.main()
