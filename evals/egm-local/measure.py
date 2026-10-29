#!/usr/bin/env python3
"""Apply the registered arithmetic gate to adjudicated semantic grades.

This is bookkeeping, not a semantic judge. It never reads model transcripts,
calls a model, or treats a regex match as evidence of design quality. The
registration, independent graders and any adjudications must be published with
the supplied evidence; this program cannot certify their independence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import prepare


ARMS = ("A", "B", "C")
CASES = ("orders", "events", "clean")
IDS = {case: (() if case == "clean" else ("C1", "C2", "M1", "M2")) for case in CASES}
STAGES = ("Initial Zoom Out", "Comprehension", "Design Critique",
          "Intermediate Zoom Out", "Implementation Readiness")


def measure(evidence, spec_sha256):
    """Fail closed on missing reviews, grades or unresolved disagreements."""
    problems = []
    if evidence.get("spec_sha256") != spec_sha256:
        problems.append("Evidence specification does not match registration")
    grading = evidence.get("grading", {})
    if grading.get("independent_graders_per_case") != 2:
        problems.append("Two independent grades per case are required")
    if grading.get("unresolved_disagreements") != []:
        problems.append("Grading disagreements remain unresolved or unreported")
    expected = {f"{case}-r{repeat}-{arm}" for case in CASES
                for repeat in range(1, 4) for arm in ARMS}
    trials = evidence.get("trials", [])
    keys = [trial.get("trial_id") for trial in trials]
    if len(keys) != len(expected) or set(keys) != expected:
        problems.append("Exactly the 27 registered trials are required")
    counts = {case: {arm: {"detections": {key: 0 for key in IDS[case]},
                          "unsupported_concrete_claims": 0,
                          "explicit_contradictions": 0,
                          "valid_additional_findings": 0} for arm in ARMS}
              for case in CASES}
    baseline_problems = []
    for trial in trials:
        name = trial.get("trial_id", "<missing>")
        case, arm = trial.get("case"), trial.get("arm")
        if case not in CASES or arm not in ARMS:
            problems.append(f"{name}: unknown case or arm")
            continue
        repeat = trial.get("repeat")
        if name != f"{case}-r{repeat}-{arm}" or repeat not in (1, 2, 3):
            problems.append(f"{name}: inconsistent trial identity")
        if trial.get("completed") is not True or trial.get("initial_inputs_intact") is not True:
            problems.append(f"{name}: incomplete review or mutated inputs")
        count = trial.get("reviewer_count")
        unique = trial.get("unique_reviewer_count")
        if type(count) is not int or count < 0 or count > 9 or unique != count:
            problems.append(f"{name}: invalid fresh-reviewer counts")
        if arm != "A":
            if count != 9:
                problems.append(f"{name}: nine fresh reviewers are required")
            stages = trial.get("stages_completed", [])
            if len(stages) != 5 or any(not any(stage in str(value) for value in stages) for stage in STAGES):
                problems.append(f"{name}: five official stages are required")
        words = trial.get("words")
        if type(words) is not int or not 0 < words <= 900:
            problems.append(f"{name}: invalid report length")
        grade = trial.get("grade", {})
        if grade.get("valid_review") is not True:
            problems.append(f"{name}: invalid or missing semantic grade")
        detections = grade.get("detected_planted_ids")
        unsupported = grade.get("unsupported_concrete_claims")
        additional = grade.get("valid_additional_findings")
        if (not isinstance(detections, list) or any(not isinstance(key, str) or key not in IDS[case] for key in detections)
                or len(detections) != len(set(detections))):
            problems.append(f"{name}: invalid or duplicate planted IDs")
            detections = []
        if not isinstance(unsupported, list) or any(
                not isinstance(item, dict) or not item.get("finding_id")
                or item.get("type") not in ("unsupported", "contradicted")
                or not item.get("reason") for item in (unsupported or [])):
            problems.append(f"{name}: malformed unsupported-claim grades")
            unsupported = []
        if len({item["finding_id"] for item in unsupported}) != len(unsupported):
            problems.append(f"{name}: duplicate unsupported-claim IDs")
        if not isinstance(additional, list):
            problems.append(f"{name}: additional findings are unreported")
            additional = []
        row = counts[case][arm]
        for key in detections:
            row["detections"][key] += 1
        row["unsupported_concrete_claims"] += len(unsupported)
        row["explicit_contradictions"] += sum(item["type"] == "contradicted" for item in unsupported)
        row["valid_additional_findings"] += len(additional)
        if arm == "A":
            if case != "clean" and not any(key.startswith("C") for key in detections):
                baseline_problems.append(f"{name}: native review detects no critical defect")
            if case == "clean" and any(item["type"] == "contradicted" for item in unsupported):
                baseline_problems.append(f"{name}: native clean review contradicts explicit source")
    comparisons = []
    for baseline, treatment in (("A", "B"), ("B", "C")):
        regressions, gains = [], []
        for case in CASES:
            before, after = counts[case][baseline], counts[case][treatment]
            for key in IDS[case]:
                delta = after["detections"][key] - before["detections"][key]
                if delta < 0:
                    regressions.append(f"{case}/{key}: detection count {before['detections'][key]} -> {after['detections'][key]}")
                elif delta > 0:
                    gains.append(f"{case}/{key}: detection count +{delta}")
            delta = after["unsupported_concrete_claims"] - before["unsupported_concrete_claims"]
            if delta > 0:
                regressions.append(f"{case}: unsupported claims +{delta}")
            elif delta < 0:
                gains.append(f"{case}: unsupported claims {delta}")
        comparisons.append({"baseline": baseline, "treatment": treatment,
                            "regressions": regressions, "gains": gains,
                            "observed_non_regression": not regressions})
    complete = not problems and not baseline_problems
    accepted = complete and all(row["observed_non_regression"] for row in comparisons)
    return {"spec_sha256": spec_sha256, "evidence_complete": complete,
            "problems": problems, "baseline_problems": baseline_problems,
            "counts": counts, "comparisons": comparisons,
            "quality_gate": "pass" if accepted else ("regression" if complete else "inconclusive"),
            "index_attribution_controls_required": bool(comparisons[1]["gains"]),
            "scope": "Observed fixed-suite non-regression only; no statistical equivalence, general superiority, cost or native-host discovery claim."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    _, checksum = prepare.verify()
    result = measure(json.loads(args.evidence.read_text(encoding="utf-8-sig")), checksum)
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result["quality_gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
