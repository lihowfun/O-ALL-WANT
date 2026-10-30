#!/usr/bin/env python3
"""Summarize observed usage and exact handoff facts; never call a model.

Citation path existence is not semantic source grounding. Independent graders
must assess review claims; this module does not invent a quality verdict.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from bench import ARMS, read, write


def expected_contract(name, stage):
    n = 17 if name == "larch" else 29
    current = stage >= 3
    return {
        "scope": "export-" + name,
        "retry_seconds": n + 7 if current else n,
        "batch_records": n * 11 if current else n * 13,
        "audit_days": n + 55 if current else n + 34,
        "dedup_fields": ["tenant_id", "request_id"],
        "active_decision": "ADR-044" if current else "ADR-040",
        "approval_ticket": f"EX-{name.upper()}-" + ("942" if current else "731"),
        "encryption_key": None,
    }


def matches(key, actual, expected):
    if key == "dedup_fields":
        return isinstance(actual, list) and all(isinstance(x, str) for x in actual) and sorted(actual) == sorted(expected)
    if type(expected) is int:
        return type(actual) is int and actual == expected
    return type(actual) is type(expected) and actual == expected


def citation_paths(value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return sorted(set(re.findall(r"[.a-zA-Z0-9_/-]+\.(?:md|txt|json)(?=[:#\s`\]\)\"',]|$)", text)))


def summarize(out):
    out = Path(out)
    manifest = read(out / "manifest.json")
    result = {"arms": {}, "memory_sessions": [], "workflow_usage": [], "review_grading": "separate independent semantic grades required", "claims": "Descriptive pilot; no statistical equivalence or general superiority"}
    expected_calls = {}
    for item in manifest["runs"]:
        expected_calls[item["id"] + "-final"] = item["arm"]
        if item["arm"] != "OAW v1":
            for role in ("implementation_readiness", "codebase_details", "style"):
                expected_calls[item["id"] + "-" + role] = item["arm"]
    for item in manifest["trajectories"]:
        for stage in range(1, 5):
            expected_calls[item["id"] + f"-s{stage}"] = item["arm"]
    for arm in ARMS:
        result["arms"][arm] = {"planned_calls": sum(a == arm for a in expected_calls.values()), "completed_calls": 0, "missing_or_incomplete": [], "input_tokens": 0, "cached_input_tokens": 0, "cache_write_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0, "usage_missing_fields": [], "memory_fields_correct": 0, "memory_fields_planned": 64, "memory_contracts_correct": 0, "memory_sessions_planned": 8, "receiver_tickets_correct": 0, "receiver_tickets_planned": 4}
    for ident, arm in expected_calls.items():
        stats = result["arms"][arm]
        path = out / "raw" / ident / "result.json"
        row = read(path) if path.exists() else {"id": ident, "status": "not_started", "usage": None}
        if row["status"] == "complete":
            stats["completed_calls"] += 1
        else:
            stats["missing_or_incomplete"].append(ident)
        usage = row.get("usage")
        for key in ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens", "reasoning_output_tokens"):
            if usage is not None and type(usage.get(key)) is int:
                stats[key] += usage[key]
            else:
                stats["usage_missing_fields"].append(ident + ":" + key)
        result["workflow_usage"].append({"id": ident, "arm": arm, **row})
    for item in manifest["trajectories"]:
        for stage in range(1, 5):
            ident = item["id"] + f"-s{stage}"
            path = out / "reports" / (ident + ".json")
            expected = expected_contract(item["name"], stage)
            answer = read(path) if path.exists() else {"answers": {}, "sources": {}}
            observed = answer["answers"]
            fields = {key: key in observed and matches(key, observed[key], value) for key, value in expected.items()}
            snapshot = out / "snapshot-files" / ident
            citations = {}
            for key, source in answer["sources"].items():
                paths = citation_paths(source)
                citations[key] = {"reported": source, "paths": paths, "all_paths_exist": bool(paths) and all((snapshot / p).is_file() for p in paths)}
            stats = result["arms"][item["arm"]]
            stats["memory_fields_correct"] += sum(fields.values())
            stats["memory_contracts_correct"] += int(all(fields.values()))
            if stage in (2, 4) and fields["approval_ticket"]:
                stats["receiver_tickets_correct"] += 1
            result["memory_sessions"].append({"id": ident, "arm": item["arm"], "stage": stage, "expected": expected, "observed": observed, "fields_correct": fields, "complete_values_correct": all(fields.values()), "citations": citations, "source_support": "Requires checking the stage-specific immutable snapshot, not merely path existence"})
    result["all_planned_calls_complete"] = all(not a["missing_or_incomplete"] for a in result["arms"].values())
    result["all_usage_fields_present"] = all(not a["usage_missing_fields"] for a in result["arms"].values())
    result["planned_final_reviews"] = len(manifest["runs"])
    result["completed_final_reports"] = sum((out / "reports" / (r["id"] + ".json")).exists() for r in manifest["runs"])
    for stats in result["arms"].values():
        stats["logical_input_plus_output_tokens"] = stats["input_tokens"] + stats["output_tokens"]
        stats["non_cached_input_tokens"] = stats["input_tokens"] - stats["cached_input_tokens"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--write", required=True)
    args = parser.parse_args()
    result = summarize(args.out)
    write(args.write, result)
    print(json.dumps({"all_planned_calls_complete": result["all_planned_calls_complete"], "completed_final_reports": result["completed_final_reports"], "arms": result["arms"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
