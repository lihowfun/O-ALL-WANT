#!/usr/bin/env python3
"""Score judge labels offline against V3-format gold; never run or approve a judge.

Gold is an object of arm|question|rep -> {labels, wrong?, wrong_at_least?,
wrong_over_e?, critical?}. Candidate JSONL rows require key and verdict with facts
and wrong_claims. See docs/CLI_Reference.md for denominators and optional metadata.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

LABELS = ("present", "absent", "contradicted")
PREDICTIONS = (*LABELS, "unknown")


class CalibrationError(ValueError):
    """Input cannot be scored without inventing observations."""


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CalibrationError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _constant(value):
    raise CalibrationError(f"non-finite JSON number: {value}")


def _decode(text):
    return json.loads(text, object_pairs_hook=_object, parse_constant=_constant)


def _require(condition, message):
    if not condition:
        raise CalibrationError(message)


def _count(value):
    return type(value) is int and value >= 0


def _parts(key):
    _require(isinstance(key, str), "key must be a string")
    parts = key.split("|")
    _require(len(parts) == 3 and all(parts) and parts[2].isascii() and parts[2].isdigit()
             and str(int(parts[2])) == parts[2] and int(parts[2]) > 0,
             f"invalid key {key!r}; expected arm|question|positive-rep")
    return parts


def load_gold(path):
    gold = _decode(Path(path).read_text(encoding="utf-8"))
    _require(isinstance(gold, dict) and gold, "gold must be a nonempty object")
    fact_ids = {}
    for key, entry in gold.items():
        _, question, _ = _parts(key)
        _require(isinstance(entry, dict) and "labels" in entry, f"{key}: gold requires labels")
        _require(not set(entry) - {"labels", "wrong", "wrong_at_least", "wrong_over_e", "critical"},
                 f"{key}: unknown gold fields")
        labels = entry["labels"]
        _require(labels is None or isinstance(labels, dict) and labels
                 and all(isinstance(fid, str) and fid and isinstance(lab, str) and lab in LABELS
                         for fid, lab in labels.items()), f"{key}: invalid gold labels")
        if labels is not None:
            ids = set(labels)
            _require(question not in fact_ids or fact_ids[question] == ids,
                     f"{key}: inconsistent fact IDs within a question")
            fact_ids[question] = ids
        checks = set(entry) & {"wrong", "wrong_at_least", "wrong_over_e"}
        _require(len(checks) <= 1 and all(_count(entry[field]) for field in checks),
                 f"{key}: wrong-claim expectation must be one nonnegative integer")
        if "wrong_over_e" in entry:
            _require(key.startswith("f|") and entry["wrong_over_e"] > 0, f"{key}: invalid f/e probe")
            _require("e|" + key[2:] in gold, f"{key}: missing e baseline")
        if "critical" in entry:
            critical = entry["critical"]
            _require(isinstance(critical, list) and all(isinstance(fid, str) for fid in critical)
                     and len(set(critical)) == len(critical) and labels is not None
                     and set(critical) <= set(labels), f"{key}: critical must list known fact IDs")
    for key in gold:
        _require(_parts(key)[1] in fact_ids, f"{key}: no known fact IDs for question")
    return gold, fact_ids


def _validate_grade(row, gold, fact_ids):
    _require(isinstance(row, dict), "grade must be an object")
    key = row.get("key")
    arm, question, rep = _parts(key)
    _require(key in gold, f"unknown answer ID: {key}")
    _require(not set(row) - {"key", "verdict", "arm", "id", "rep", "coverage", "essential_ok",
                             "contradicted", "_grader", "status", "error"}, f"{key}: unknown grade fields")
    _require(row.get("status", "completed") in ("completed", "ok") and row.get("error") is None,
             f"{key}: grade did not run or did not complete")
    for field, expected in (("arm", arm), ("id", question), ("rep", int(rep))):
        if field in row:
            _require(type(row[field]) is type(expected) and row[field] == expected,
                     f"{key}: {field} disagrees with key")
    verdict = row.get("verdict")
    _require(isinstance(verdict, dict) and not set(verdict) - {"facts", "wrong_claims", "note", "_grader_tokens"},
             f"{key}: malformed verdict")
    facts = verdict.get("facts")
    _require(isinstance(facts, dict), f"{key}: facts must be an object")
    missing, extra = fact_ids[question] - set(facts), set(facts) - fact_ids[question]
    _require(not missing and not extra,
             f"{key}: missing label IDs {sorted(missing)}; unknown label IDs {sorted(extra)}")
    _require(all(isinstance(label, str) and label in PREDICTIONS for label in facts.values()),
             f"{key}: unknown label; use present, absent, contradicted, or explicit unknown")
    _require(_count(verdict.get("wrong_claims")), f"{key}: wrong_claims requires a nonnegative integer")
    if "_grader_tokens" in verdict:
        _require(_count(verdict["_grader_tokens"]) and verdict["_grader_tokens"] > 0,
                 f"{key}: invalid tokens or grade did not run (zero tokens)")
    # Archived derived fields are never trusted for scoring, but their schemas still matter.
    if "coverage" in row:
        _require(type(row["coverage"]) in (int, float) and 0 <= row["coverage"] <= 1,
                 f"{key}: invalid archived coverage")
    if "essential_ok" in row:
        _require(type(row["essential_ok"]) is bool, f"{key}: invalid essential_ok")
    if "contradicted" in row:
        _require(_count(row["contradicted"]), f"{key}: invalid contradicted count")
    if "note" in verdict:
        _require(isinstance(verdict["note"], str), f"{key}: note must be a string")
    if "_grader" in row:
        _require(isinstance(row["_grader"], dict)
                 and not set(row["_grader"]) - {"backend", "model", "effort", "order"}
                 and all(isinstance(v, str) for v in row["_grader"].values()), f"{key}: malformed _grader")
    return key


def load_grades(path, gold, fact_ids):
    grades, seen, errors = {}, set(), []
    try:
        with Path(path).open(encoding="utf-8") as handle:
            for line, text in enumerate(handle, 1):
                try:
                    row = _decode(text)
                    key = _validate_grade(row, gold, fact_ids)
                    _require(key not in seen, f"duplicate answer ID: {key}")
                    seen.add(key)
                    grades[key] = row["verdict"]
                except ValueError as exc:
                    errors.append(f"line {line}: {exc}")
    except (OSError, UnicodeError) as exc:
        errors.append(str(exc))
    missing = sorted(set(gold) - set(grades))
    if missing:
        errors.append("missing valid grades: " + ", ".join(missing))
    # Reject the whole candidate: a partial dataset must not acquire a score.
    return grades, errors


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def score(gold, grades):
    """Count observations only; infer no admission verdict or statistical superiority."""
    confusion = {label: dict.fromkeys(PREDICTIONS, 0) for label in LABELS}
    right = known = abstained = all_cells = all_unknown = 0
    by_variant, wrong_checks, planted, consistency = {}, {}, [], []
    errors, false_credit, critical_errors, critical_unknown = [], [], [], []
    critical_total = 0
    tokens = []
    probes = []
    for key, entry in gold.items():
        variant, _, _ = _parts(key)
        verdict = grades[key]
        facts, wrong = verdict["facts"], verdict["wrong_claims"]
        all_cells += len(facts)
        all_unknown += sum(label == "unknown" for label in facts.values())
        if "_grader_tokens" in verdict:
            tokens.append(verdict["_grader_tokens"])
        labels = entry["labels"]
        if labels is not None:
            hits = sum(facts[fid] == label for fid, label in labels.items())
            right += hits
            known += len(labels)
            by_variant.setdefault(variant, [0, 0])
            by_variant[variant][0] += hits
            by_variant[variant][1] += len(labels)
            for fid, label in labels.items():
                predicted = facts[fid]
                confusion[label][predicted] += 1
                cell = {"key": key, "fact": fid, "gold": label, "predicted": predicted}
                if predicted == "unknown":
                    abstained += 1
                elif predicted != label:
                    errors.append(cell)
                if predicted == "present" and label != "present":
                    false_credit.append(cell)
                if fid in entry.get("critical", []):
                    critical_total += 1
                    if predicted == "unknown":
                        critical_unknown.append(cell)
                    elif predicted != label:
                        critical_errors.append(cell)
        if "wrong" in entry or "wrong_at_least" in entry:
            field = "wrong" if "wrong" in entry else "wrong_at_least"
            threshold = entry[field]
            name = f"{variant}_wrong_{'is' if field == 'wrong' else 'at_least'}_{threshold}"
            passed = wrong == threshold if field == "wrong" else wrong >= threshold
            wrong_checks.setdefault(name, []).append(passed)
        if "wrong_over_e" in entry:
            baseline = grades["e|" + key[2:]]
            delta = wrong - baseline["wrong_claims"]
            planted.append(delta)
            probes.append({"key": key, "expected_delta": entry["wrong_over_e"], "observed_delta": delta,
                           "detected": delta >= entry["wrong_over_e"], "partial_or_better": delta >= 1})
            consistency.append(sum(label == facts[fid] for fid, label in baseline["facts"].items()) / len(facts))
    # Keep the archived V3 field names and three-decimal rounding for exact replay.
    rounded = lambda value: round(value, 3) if value is not None else None
    return {
        "graded": len(grades), "known_label_cells": known,
        "label_accuracy_a_to_d": rounded(_ratio(right, known)),
        "label_accuracy_by_variant": {v: rounded(_ratio(h, t)) for v, (h, t) in sorted(by_variant.items())},
        "wrong_claim_checks": {name: f"{sum(values)}/{len(values)}" for name, values in wrong_checks.items()},
        "planted_wrong_delta_f_minus_e": planted,
        "planted_detected_rate": rounded(_ratio(sum(p["detected"] for p in probes), len(probes))),
        "planted_partial_or_better_rate": rounded(_ratio(sum(p["partial_or_better"] for p in probes), len(probes))),
        "e_f_label_consistency": rounded(_ratio(sum(consistency), len(consistency))),
        "injected_pairs": probes,
        "confusion": confusion,
        "label_errors": errors,
        "abstention": {"known_cells": abstained, "known_rate": _ratio(abstained, known),
                       "coverage": _ratio(known - abstained, known), "covered_accuracy": _ratio(right, known - abstained),
                       "all_cells": all_cells, "all_unknown": all_unknown, "all_rate": _ratio(all_unknown, all_cells)},
        "false_credit": {"count": len(false_credit), "cells": false_credit},
        "critical_misses": {"evaluated_cells": critical_total,
                            "count": len(critical_errors) if critical_total else None, "cells": critical_errors,
                            "abstained": len(critical_unknown) if critical_total else None,
                            "abstention_cells": critical_unknown},
        "token_cost": {"recorded_tokens": sum(tokens) if tokens else None, "recorded_grades": len(tokens),
                       "missing_grades": len(grades) - len(tokens), "complete": len(tokens) == len(grades)},
    }


def render_text(report):
    lines = ["Offline judge calibration; no judge installed or approved."]
    lines.extend("REJECTED gold: " + error for error in report.get("errors", []))
    for candidate in report["candidates"]:
        lines.append(f"{candidate['file']}: {candidate['status']}")
        if candidate["status"] == "rejected":
            lines.extend("  " + error for error in candidate["errors"])
            continue
        metrics = candidate["metrics"]
        for field in ("graded", "known_label_cells", "label_accuracy_a_to_d", "label_accuracy_by_variant",
                      "abstention", "false_credit", "critical_misses", "wrong_claim_checks", "injected_pairs",
                      "planted_wrong_delta_f_minus_e", "planted_detected_rate", "planted_partial_or_better_rate",
                      "e_f_label_consistency", "token_cost", "label_errors"):
            lines.append(f"  {field}: {json.dumps(metrics[field], ensure_ascii=False)}")
        lines.append("  confusion (gold -> predicted): " + ", ".join(PREDICTIONS))
        lines.extend(f"    {label}: " + ", ".join(str(count) for count in counts.values())
                     for label, counts in metrics["confusion"].items())
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gold", help="V3-format expected.json")
    parser.add_argument("grades", nargs="+", help="one or more V3-format candidate JSONL files")
    parser.add_argument("--json", action="store_true", help="emit machine-readable report")
    args = parser.parse_args(argv)
    report = {"schema_version": 1, "status": "scored", "candidates": []}
    try:
        gold, fact_ids = load_gold(args.gold)
    except (OSError, ValueError, UnicodeError) as exc:
        report.update(status="rejected", errors=[str(exc)])
    else:
        for path in args.grades:
            grades, errors = load_grades(path, gold, fact_ids)
            candidate = {"file": path, "status": "rejected" if errors else "scored"}
            if errors:
                candidate["errors"] = errors
                report["status"] = "rejected"
            else:
                candidate["metrics"] = score(gold, grades)
            report["candidates"].append(candidate)
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) if args.json else render_text(report))
    return 2 if report["status"] == "rejected" else 0


if __name__ == "__main__":
    raise SystemExit(main())
