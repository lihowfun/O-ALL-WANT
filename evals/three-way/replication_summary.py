#!/usr/bin/env python3
"""Exact gold precision and agreement on identically seeded fresh receivers."""
import argparse
from itertools import combinations
from pathlib import Path
from bench import ARMS, read, write
from summarize import expected_contract, matches


def agreement(answers, expected):
    agreed = possible = 0
    for a, b in combinations(answers, 2):
        for key in expected:
            possible += 1
            # A shared missing field is not an agreement on an actual answer.
            if key not in a or key not in b:
                continue
            if key == "dedup_fields":
                same = isinstance(a[key], list) and isinstance(b[key], list) and matches(key, a[key], b[key])
            else:
                same = type(a[key]) is type(b[key]) and a[key] == b[key]
            agreed += int(same)
    correct = [all(key in a and matches(key, a[key], value) for key, value in expected.items()) for a in answers]
    return {"pairwise_fields_agree": agreed, "pairwise_fields_planned": possible,
            "complete_contracts_correct": sum(correct), "receivers_planned": len(answers),
            "unanimous_correct": all(correct)}


def summarize(cohort, replication):
    cohort, replication = Path(cohort), Path(replication)
    manifest = read(cohort / "manifest.json")
    result = {"arms": {}, "snapshots": [], "note": "Original S2 is reused as one observation; these are not new independent trajectory families. Agreement is separate from gold correctness; semantic citation grounding is graded separately."}
    for arm in ARMS:
        result["arms"][arm] = {"fields_correct": 0, "fields_planned": 48, "complete_contracts_correct": 0, "receivers_planned": 6, "pairwise_fields_agree": 0, "pairwise_fields_planned": 48, "unanimous_correct_snapshots": 0, "snapshots_planned": 2, "additional_calls_complete": 0, "additional_calls_planned": 4, "additional_input_tokens": 0, "additional_output_tokens": 0, "additional_cached_input_tokens": 0}
    for item in manifest["trajectories"]:
        paths = [cohort / "reports" / (item["id"] + "-s2.json")] + [replication / "reports" / (item["id"] + f"-receiver{r}.json") for r in (2, 3)]
        answers = [read(p)["answers"] if p.exists() else {} for p in paths]
        expected = expected_contract(item["name"], 2)
        metrics = agreement(answers, expected)
        stats = result["arms"][item["arm"]]
        stats["fields_correct"] += sum(key in a and matches(key, a[key], value) for a in answers for key, value in expected.items())
        stats["complete_contracts_correct"] += metrics["complete_contracts_correct"]
        stats["pairwise_fields_agree"] += metrics["pairwise_fields_agree"]
        stats["unanimous_correct_snapshots"] += int(metrics["unanimous_correct"])
        for repeat in (2, 3):
            row_path = replication / "raw" / (item["id"] + f"-receiver{repeat}") / "result.json"
            if row_path.exists():
                row = read(row_path)
                stats["additional_calls_complete"] += int(row["status"] == "complete" and row.get("io_verified") is True)
                if row.get("usage"):
                    for key in ("input_tokens", "output_tokens", "cached_input_tokens"):
                        stats["additional_" + key] += row["usage"][key]
        result["snapshots"].append({"id": item["id"], "arm": item["arm"], "answers": answers, **metrics})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", required=True)
    parser.add_argument("--replication", required=True)
    parser.add_argument("--write", required=True)
    args = parser.parse_args()
    result = summarize(args.cohort, args.replication)
    write(args.write, result)
    print(result["arms"])
