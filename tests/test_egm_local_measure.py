"""Arithmetic acceptance regressions; synthetic grades are not quality evidence."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "evals/egm-local"
sys.path.insert(0, str(SOURCE))
SPEC = importlib.util.spec_from_file_location("egm_local_measure", SOURCE / "measure.py")
measurement = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(measurement)
ANON_SPEC = importlib.util.spec_from_file_location("egm_local_anonymize", SOURCE / "anonymize.py")
anonymizer = importlib.util.module_from_spec(ANON_SPEC)
ANON_SPEC.loader.exec_module(anonymizer)
sys.path.pop(0)


def synthetic_evidence():
    trials = []
    for case in measurement.CASES:
        for repeat in (1, 2, 3):
            for arm in measurement.ARMS:
                trials.append({
                    "trial_id": f"{case}-r{repeat}-{arm}", "case": case,
                    "repeat": repeat, "arm": arm, "completed": True,
                    "initial_inputs_intact": True, "reviewer_count": 1 if arm == "A" else 9,
                    "unique_reviewer_count": 1 if arm == "A" else 9,
                    "stages_completed": list(measurement.STAGES), "words": 400,
                    "grade": {"valid_review": True,
                              "detected_planted_ids": list(measurement.IDS[case]),
                              "unsupported_concrete_claims": [], "valid_additional_findings": []},
                })
    return {"spec_sha256": "synthetic", "trials": trials,
            "grading": {"independent_graders_per_case": 2, "unresolved_disagreements": []}}


class LocalMeasurementTests(unittest.TestCase):
    def test_complete_equal_grades_pass_without_improvement_claim(self):
        result = measurement.measure(synthetic_evidence(), "synthetic")
        self.assertEqual(result["quality_gate"], "pass")
        self.assertTrue(result["evidence_complete"])
        self.assertTrue(all(not row["gains"] for row in result["comparisons"]))
        self.assertFalse(result["index_attribution_controls_required"])

    def test_per_defect_regression_cannot_be_hidden_by_total_gain(self):
        evidence = synthetic_evidence()
        # A misses one major; B gains it but misses a different critical.
        evidence["trials"][0]["grade"]["detected_planted_ids"].remove("M1")
        evidence["trials"][1]["grade"]["detected_planted_ids"].remove("C1")
        result = measurement.measure(evidence, "synthetic")
        self.assertEqual(result["quality_gate"], "regression")
        self.assertIn("orders/C1", result["comparisons"][0]["regressions"][0])

    def test_false_claim_regression_is_counted_per_case(self):
        evidence = synthetic_evidence()
        evidence["trials"][-1]["grade"]["unsupported_concrete_claims"] = [
            {"finding_id": "F01", "type": "contradicted", "reason": "Synthetic source says otherwise"}]
        result = measurement.measure(evidence, "synthetic")
        self.assertEqual(result["quality_gate"], "regression")
        self.assertEqual(result["counts"]["clean"]["C"]["explicit_contradictions"], 1)

    def test_missing_invalid_or_unresolved_evidence_is_inconclusive(self):
        original = synthetic_evidence()
        candidates = []
        missing = deepcopy(original)
        missing["trials"].pop()
        candidates.append(missing)
        for key, value in (("completed", False), ("initial_inputs_intact", False),
                           ("reviewer_count", 8), ("stages_completed", []), ("words", 901)):
            changed = deepcopy(original)
            changed["trials"][1][key] = value
            candidates.append(changed)
        disagreement = deepcopy(original)
        disagreement["grading"]["unresolved_disagreements"] = ["orders/R01/C1"]
        candidates.append(disagreement)
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                self.assertEqual(measurement.measure(candidate, "synthetic")["quality_gate"], "inconclusive")

    def test_baseline_floor_and_duplicate_detection_rejected(self):
        evidence = synthetic_evidence()
        evidence["trials"][0]["grade"]["detected_planted_ids"] = ["M1", "M2"]
        self.assertEqual(measurement.measure(evidence, "synthetic")["quality_gate"], "inconclusive")
        evidence = synthetic_evidence()
        evidence["trials"][1]["grade"]["detected_planted_ids"].append("C1")
        self.assertEqual(measurement.measure(evidence, "synthetic")["quality_gate"], "inconclusive")

    def test_c_gain_requires_controls_before_index_attribution(self):
        evidence = synthetic_evidence()
        evidence["trials"][1]["grade"]["detected_planted_ids"].remove("M1")
        result = measurement.measure(evidence, "synthetic")
        self.assertTrue(result["index_attribution_controls_required"])
        # B's loss still blocks overall acceptance despite C recovering it.
        self.assertEqual(result["quality_gate"], "regression")

    def test_anonymization_preserves_claims_and_uncertainties(self):
        report = {"claim": "Atomicity is missing", "location": "C:\\fixture\\orders-r1-C\\docs/design.md:10",
                  "uncertainties": ["Question: is another transaction intended?", "Uses literal \\n."]}
        changed = anonymizer.normalize(report, [{"workspace": "C:/fixture/orders-r1-C"}])
        self.assertEqual(changed["location"], "docs/design.md:10")
        self.assertEqual(changed["claim"], report["claim"])
        self.assertEqual(changed["uncertainties"], report["uncertainties"])
        self.assertEqual(report["location"], "C:\\fixture\\orders-r1-C\\docs/design.md:10")

    def test_official_stage_label_variants_preserve_same_five_stages(self):
        evidence = synthetic_evidence()
        evidence["trials"][1]["stages_completed"] = [
            "5 Initial Zoom Out: initial_zoom", "6 Comprehension: comprehension",
            "7 Critic: critic_design, critic_structural, critic_style",
            "8 Intermediate Zoom Out: intermediate_zoom",
            "9 Implementation Readiness: readiness_implementation, readiness_codebase, readiness_style"]
        self.assertEqual(measurement.measure(evidence, "synthetic")["quality_gate"], "pass")
        evidence["trials"][1]["stages_completed"][2] = "7 unspecified"
        self.assertEqual(measurement.measure(evidence, "synthetic")["quality_gate"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
