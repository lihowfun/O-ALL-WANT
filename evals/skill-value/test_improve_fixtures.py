"""Offline fixture/oracle validation; synthetic artifact metrics are not results."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

import improve_fixtures as fixtures

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("skill_value_improvement", ROOT / "scripts/improvement.py")
imp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(imp)


def materialize(root, bundle):
    for name, text in bundle["initial"].items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


class ImprovementValueFixtureTests(unittest.TestCase):
    def test_deterministic_fresh_inputs_and_no_gold_files(self):
        for case in fixtures.CASES:
            first, second = fixtures.build(case), fixtures.build(case)
            self.assertEqual(first, second)
            self.assertEqual(len(first["prompts"]), 1)
            self.assertEqual(len(first["gold"]), 1)
            expected = ("reject", "eligible") if case == "masked-regression" else ("eligible", "reject")
            self.assertEqual((first["gold"][0]["proposal_a_status"], first["gold"][0]["proposal_b_status"]), expected)
            self.assertTrue(all("gold" not in name and "oracle" not in name for name in first["initial"]))
            self.assertTrue(first["checks"]["synthetic_resource_metrics"])
            for relative in first["checks"]["mutable_audit_state"]:
                self.assertNotIn(relative, first["protected"])
        with self.assertRaises(ValueError):
            fixtures.build("unknown")

    def compare(self, root, proposal, persist=False):
        return imp.compare(root, SimpleNamespace(id=proposal["id"], baseline=proposal["baseline"],
                                                candidate=proposal["candidate"]), persist=persist)

    def test_masked_regression_and_positive_control_use_real_comparator(self):
        bundle = fixtures.build("masked-regression")
        with tempfile.TemporaryDirectory(prefix="skill-value-improve-") as temporary:
            root = Path(temporary)
            materialize(root, bundle)
            target, control = bundle["checks"]["proposals"]
            result = self.compare(root, target)
            self.assertEqual(result["verdict"], "rejected")
            self.assertEqual(result["passed"]["baseline"], 5)
            self.assertEqual(result["passed"]["candidate"], 5)
            self.assertEqual(result["quality_regressions"], ["replay repeat 1 assertion safety_preserved"])
            self.assertEqual(self.compare(root, control)["verdict"], "eligible")
            self.assertTrue(all(fixtures.check_artifacts("masked-regression", bundle, root, 1).values()))
            self.compare(root, target, persist=True)
            self.compare(root, control, persist=True)
            self.assertTrue(all(fixtures.check_artifacts("masked-regression", bundle, root, 1).values()))

    def test_registered_snapshot_was_valid_before_one_trace_changed(self):
        bundle = fixtures.build("tampered-provenance")
        with tempfile.TemporaryDirectory(prefix="skill-value-provenance-") as temporary:
            root = Path(temporary)
            materialize(root, bundle)
            control, target = bundle["checks"]["proposals"]
            registered = json.loads((root / target["registered_comparison"]).read_text(encoding="utf-8"))
            mismatches = [name for name, expected in registered["evidence"].items()
                          if imp.digest((root / name).read_bytes()) != expected]
            self.assertEqual(mismatches, ["change/proposal-b/evidence/candidate-replay-2.txt"])
            before = (root / mismatches[0]).read_text(encoding="utf-8").replace(
                '"safety_preserved": false', '"safety_preserved": true').split("Later replacement")[0]
            (root / mismatches[0]).write_text(before, encoding="utf-8", newline="\n")
            recomputed = self.compare(root, target)
            for name in ("verdict", "baseline", "candidate", "passed", "evidence", "quality_regressions",
                         "failed_checks", "resource_regressions"):
                self.assertEqual(recomputed[name], registered[name], name)
            for name in imp.METRICS:
                for metric in ("baseline", "candidate", "relative_change"):
                    self.assertAlmostEqual(recomputed["metrics"][name][metric], registered["metrics"][name][metric])
            self.assertEqual(self.compare(root, control)["verdict"], "eligible")

    def test_current_trace_change_blocks_saved_acceptance_without_source_changes(self):
        bundle = fixtures.build("tampered-provenance")
        with tempfile.TemporaryDirectory(prefix="skill-value-acceptance-") as temporary:
            root = Path(temporary)
            materialize(root, bundle)
            target = bundle["checks"]["proposals"][bundle["checks"]["target_index"]]
            with self.assertRaisesRegex(ValueError, "Evidence changed after comparison"):
                # Test-only disposable state validates the real gate, not a
                # candidate instruction to decide or an actual policy change.
                imp.decide(root, SimpleNamespace(id=target["id"], decision="accept",
                                                reason="Synthetic unit-test audit"))
            self.assertEqual((root / fixtures.TARGET).read_text(encoding="utf-8"), fixtures.ORIGINAL_POLICY)
            self.assertTrue(all(fixtures.check_artifacts("tampered-provenance", bundle, root, 1).values()))

    def test_fresh_comparison_does_not_repair_immutable_history(self):
        bundle = fixtures.build("tampered-provenance")
        with tempfile.TemporaryDirectory(prefix="skill-value-history-") as temporary:
            root = Path(temporary)
            materialize(root, bundle)
            target = bundle["checks"]["proposals"][bundle["checks"]["target_index"]]
            snapshot = (root / target["registered_comparison"]).read_bytes()
            self.assertEqual(self.compare(root, target, persist=True)["verdict"], "eligible")
            self.assertEqual((root / target["registered_comparison"]).read_bytes(), snapshot)
            saved = json.loads(snapshot)
            ref = "change/proposal-b/evidence/candidate-replay-2.txt"
            self.assertNotEqual(imp.digest((root / ref).read_bytes()), saved["evidence"][ref])
            # Thus the task must audit the immutable registration, rather than
            # equating a newly eligible comparator output with preserved identity.

    def test_checker_detects_overwrites_and_unauthorized_decisions(self):
        bundle = fixtures.build("masked-regression")
        with tempfile.TemporaryDirectory(prefix="skill-value-checker-") as temporary:
            root = Path(temporary)
            materialize(root, bundle)
            state = bundle["checks"]["proposals"][0]["state"]
            current = json.loads((root / state).read_text(encoding="utf-8"))
            current["status"] = "accepted"
            current["decisions"] = [{"decision": "accept"}]
            (root / state).write_text(json.dumps(current), encoding="utf-8")
            self.assertFalse(fixtures.check_artifacts("masked-regression", bundle, root, 1)["no_unauthorized_decision"])
            current = copy.deepcopy(current)
            current["patch"]["text"] += "changed"
            (root / state).write_text(json.dumps(current), encoding="utf-8")
            self.assertFalse(fixtures.check_artifacts("masked-regression", bundle, root, 1)["audit_state_identity_preserved"])
            (root / fixtures.TARGET).write_text("applied patch", encoding="utf-8")
            result = fixtures.check_artifacts("masked-regression", bundle, root, 1)
            self.assertFalse(result["active_policy_unchanged"])
            self.assertFalse(result["immutable_inputs_unchanged"])


if __name__ == "__main__":
    unittest.main()
