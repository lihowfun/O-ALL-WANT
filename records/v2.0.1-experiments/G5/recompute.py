#!/usr/bin/env python3
"""Recompute historical accounting only; never execute runners or graders."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
RECORDS = HERE.parents[2]
SETS = {
    "graphify_oaw_agent": ("records/digestion-2026-11-03/taste-graphify/agent/out", 18),
    "graphify_erpnext_initial": ("records/digestion-2026-11-03/taste-graphify/erpnext/out", 8),
    "erpnext_confirm_opus": ("records/digestion-2026-11-03/codemap-erpnext-confirm/out-opus", 36),
    "erpnext_confirm_sonnet": ("records/digestion-2026-11-03/codemap-erpnext-confirm/out-sonnet", 36),
    "erpnext_weaker_opus48": ("records/digestion-2026-11-03/codemap-erpnext-weaker/out/opus48", 36),
    "erpnext_weaker_haiku": ("records/digestion-2026-11-03/codemap-erpnext-weaker/out/haiku", 36),
    "erpnext_four_arm_opus": ("records/digestion-2026-11-06/taste-codegraph/out-opus", 48),
    "erpnext_four_arm_sonnet": ("records/digestion-2026-11-06/taste-codegraph/out-sonnet", 48),
    "erpnext_four_arm_opus48": ("records/digestion-2026-11-06/taste-codegraph/out-opus48", 48),
    "erpnext_four_arm_haiku": ("records/digestion-2026-11-06/taste-codegraph/out-haiku", 48),
    "codegraph_nb": ("records/digestion-2026-11-06/taste-codegraph/out-nb-opus", 12),
    "codegraph_v8": ("records/digestion-2026-11-07/validation/v8/out", 24),
    "oaw_x1_opus": ("records/v2.0.1-experiments/X1/out-opus", 24),
    "oaw_x1_codex": ("records/v2.0.1-experiments/X1/out-codex", 24),
    "tokeneconomizer_initial": ("records/digestion-2026-11-03/taste-tokeneconomizer", 24),
    "tokeneconomizer_envfacts": ("records/digestion-2026-11-03/taste-tokeneconomizer/followup-envfacts", 12),
}


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(values):
    known = [v for v in values if v is not None]
    return {"observed": sum(known), "unknown_entries": len(values) - len(known),
            "complete": len(known) == len(values),
            "total": sum(known) if len(known) == len(values) else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-root", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "schema": "g5-historical-accounting/1",
        "schema1_ledger_bundle": False,
        "note": "Historical row accounting, not an eligibility certificate or eval_ledger report. Dataset views overlap; never sum them.",
        "unknown": None,
        "sources": {}, "datasets": {}, "cross_family_regrades": {},
        "whole_study": {"logical_tokens": None, "noncache_tokens": None, "cost_usd": None, "elapsed_seconds": None,
                        "reason": "Unmetered controller/review work and at least one unrecorded failed codegraph attempt."},
    }

    def source(path):
        rel = path.relative_to(RECORDS).as_posix()
        result["sources"][rel] = {"sha256": digest(path)}
        return rel

    data = {}
    for label, (rel, planned) in SETS.items():
        directory = RECORDS / rel
        row_path = directory / "rows.jsonl"
        rows = read_rows(row_path)
        data[label] = rows
        grades = {}
        for path in sorted(directory.glob("grades*.jsonl")):
            entries = read_rows(path)
            mechanical = bool(entries) and all(e.get("grader", "").startswith("mechanical:") for e in entries)
            counts = [0 if mechanical else e.get("verdict", {}).get("_grader_tokens") for e in entries]
            grades[path.name] = {
                "source": source(path), "attempt_rows": len(entries),
                "valid_scored": sum((e.get("correct") is not None) if mechanical else
                                    (e.get("coverage") is not None and e.get("verdict", {}).get("_grader_tokens", 0) > 0)
                                    for e in entries),
                "zero_token_not_run": 0 if mechanical else sum(v == 0 for v in counts),
                "mechanical": mechanical,
                "stage": "grading", "logical_tokens": metrics(counts),
                "noncache_tokens": None, "cost_usd": None, "elapsed_seconds": None,
            }
        identities = [(r["arm"], r["id"], r.get("rep", 1)) for r in rows]
        assert len(identities) == len(set(identities)), label
        arms = {}
        for arm in sorted({r["arm"] for r in rows}):
            rr = [r for r in rows if r["arm"] == arm]
            sidecalls = [c for r in rr for c in r.get("sidecalls", [])]
            arms[arm] = {
                "completed_rows": len(rr), "seeded_rows": sum(bool(r.get("seeded")) for r in rr),
                "task_count": len({r["id"] for r in rr}),
                "answer": {"logical_tokens": metrics([r.get("tokens_total") for r in rr]),
                           "noncache_tokens": None,
                           "cost_usd": metrics([r.get("cost_usd") for r in rr]),
                           "elapsed_seconds": metrics([r.get("seconds") for r in rr])},
                "proposal_sidecalls": {"completed_calls": len(sidecalls),
                                       "logical_tokens": sum(r.get("sidecall_tokens_total", 0) for r in rr),
                                       "elapsed_seconds": metrics([c.get("seconds") for c in sidecalls]) if sidecalls else None,
                                       "note": "Separate food sidecalls; not included in answer logical tokens."},
                "map_commands": sum(r.get("map_commands", 0) for r in rr) if label.startswith("oaw_x1") else None,
            }
        result["datasets"][label] = {
            "rows_source": source(row_path), "planned": planned,
            "started_observed": len(rows), "started_all_attempts": None,
            "started_lower_bound": len(rows) + (1 if label == "erpnext_four_arm_opus48" else 0),
            "completed": len(rows),
            "scored": grades.get("grades.jsonl", grades.get("grades-opus.jsonl", {})).get("valid_scored"),
            "missing_planned_outputs": planned - len(rows),
            "missing_reason": "NB repeat 3 stopped by registered budget guard" if label == "codegraph_nb" else None,
            "grading_passes": grades, "arms": arms,
            "shared_stages": {"authoring": None, "review": None, "controller": None},
        }
    for condition in ["opus", "sonnet", "opus48", "haiku"]:
        directory = RECORDS / "records/digestion-2026-11-07/validation/v4" / condition
        result["cross_family_regrades"][condition] = {}
        for path in sorted(directory.glob("grades-codex-*.jsonl")):
            rows = read_rows(path)
            result["cross_family_regrades"][condition][path.name] = {
                "source": source(path), "planned": 48, "completed": len(rows),
                "scored": sum(r.get("coverage") is not None and r.get("verdict", {}).get("_grader_tokens", 0) > 0 for r in rows),
                "logical_tokens": metrics([r.get("verdict", {}).get("_grader_tokens") for r in rows]),
            }
    # These are separate diagnostic tool trials, never agent answers.
    result["tool_diagnostics"] = {}
    for label, rel in [
        ("oaw_invalid_first", "records/digestion-2026-11-03/codemap-stage0/run1-invalid-R-not-executed/results.json"),
        ("oaw_stage0", "records/digestion-2026-11-03/codemap-stage0/run2/results.json"),
        ("graphify_stage0", "records/digestion-2026-11-03/taste-graphify/results.json"),
    ]:
        path = RECORDS / rel
        obj = json.loads(path.read_text())
        result["tool_diagnostics"][label] = {"source": source(path), "planned_cells": len(obj["rows"]),
            "serialized_cells": len(obj["rows"]), "failed_cells": sum(bool(r["failed"]) for r in obj["rows"]),
            "arms": dict(Counter(r["arm"] for r in obj["rows"])), "model_logical_tokens": 0,
            "note": "A serialized zero/error in an invalid diagnostic is not a scored agent answer."}
    for rel in [
        "records/audit-2026-11-08/CODEX_AUDIT.md",
        "records/digestion-2026-11-03/ingest/DECISIONS.md",
        "records/digestion-2026-11-03/taste-tokeneconomizer/PREREG.md",
        "records/digestion-2026-11-03/taste-tokeneconomizer/tasks.json",
        "records/digestion-2026-11-03/taste-tokeneconomizer/verify.json",
        "records/digestion-2026-11-03/taste-tokeneconomizer/followup-envfacts/PREREG.md",
        "records/digestion-2026-11-03/taste-graphify/erpnext/questions.json",
        "records/digestion-2026-11-06/taste-codegraph/PREREG.md",
        "records/digestion-2026-11-06/taste-codegraph/taste_run.py",
        "records/digestion-2026-11-07/validation/v8/questions.json",
        "records/digestion-2026-11-07/validation/v8/ADDENDUM-V8.md",
        "records/v2.0.1-experiments/X1/PREREG.md",
        "records/v2.0.1-experiments/X1/questions.json",
        "records/v2.0.1-experiments/X1/floor_sd.json",
    ]:
        source(RECORDS / rel)
    result["product_sources"] = {rel: {"sha256": digest(args.product_root / rel)} for rel in
                                 ["docs/EVAL_PROTOCOL.md", "docs/EVAL_LEDGER.md", "scripts/eval_stats.py",
                                  "scripts/eval_ledger.py", "catalog/verdicts.json", "docs/intake/graphify-map.md"]}
    result["shared_cost_observations"] = {
        "tokeneconomizer_authoring": {"logical_tokens": 6539760, "source": "records/digestion-2026-11-03/taste-tokeneconomizer/PREREG.md:18"},
        "x1_authoring": {"logical_tokens": 20068719, "source": "records/v2.0.1-experiments/X1/PREREG.md:45"},
        "x1_haiku_pilots": {"logical_tokens": 2045818, "runs": 4, "source": "records/v2.0.1-experiments/X1/PREREG.md:98"},
        "codegraph_sonnet_pilot": {"logical_tokens": 43368, "runs": 1, "source": "records/digestion-2026-11-06/taste-codegraph/PREREG.md:41"},
        "controller": None, "independent_review": None,
    }
    write("ACCOUNTING.json", result)

    def estimate(unit, runs, source_label, note):
        return {"pilot_unit_logical_tokens": unit, "runs": runs, "factor": 1.3,
                "estimated_logical_tokens": math.ceil(unit * runs * 1.3),
                "pilot_source": source_label, "note": note}

    v8_unit = sum(r["tokens_total"] for r in data["codegraph_v8"]) / 24
    home_unit = sum(r["tokens_total"] for r in data["erpnext_weaker_opus48"]) / 36
    haiku_unit = sum(r["tokens_total"] for r in data["erpnext_weaker_haiku"]) / 36
    te_unit = sum(r["tokens_total"] + r.get("sidecall_tokens_total", 0) for label in
                  ["tokeneconomizer_initial", "tokeneconomizer_envfacts"] for r in data[label]) / 36
    v8_grade = sum(g["logical_tokens"]["observed"] for g in result["datasets"]["codegraph_v8"]["grading_passes"].values()) / 48
    estimates = {
        "schema": "g5-rerun-planning/1", "executed": False,
        "note": "Costs are planning estimates, not approvals, power guarantees, or whole-study totals. Except the documented Sonnet probe, old scored rows are explicitly used as pilot surrogates.",
        "codegraph_true_pilot_lower_fidelity": estimate(43368, 60, "codegraph Sonnet probe, 1 run; PREREG.md:41", "Different model/repository from VS Code home turf; do not use as a dependable budget."),
        "codegraph_home_turf_surrogate": estimate(v8_unit, 60, "codegraph_v8: 24 N/C answers", "24 new N calibration answers (12 tasks x 2), then 36 N/C/M test answers; M cost is unmeasured on VS Code."),
        "codegraph_grading_surrogate": estimate(v8_grade, 120, "codegraph_v8: 48 Opus/Codex grades", "Two families grade all 60 calibration/test answers."),
        "graphify_home_turf_surrogate": estimate(home_unit, 60, "erpnext_weaker_opus48: 36 N/G/S answers", "24 new N calibration answers, then 36 N/G/M test answers."),
        "graphify_haiku_surrogate": estimate(haiku_unit, 60, "erpnext_weaker_haiku: 36 N/G/S answers", "Same design, separate Haiku condition, including existing warning scope."),
        "graphify_grading_surrogate": estimate(v8_grade, 240, "codegraph_v8: 48 Opus/Codex grades", "Proxy only; graphify prompt/task lengths may differ."),
        "tokeneconomizer_single_stream_pair_pilot": estimate(te_unit, 92, "36 N/T/T2 historical sessions, incl. 4 proposer calls", "One 46-session N/T2 stream pair; only a pilot, not 12 independent D32 units."),
        "tokeneconomizer_envfacts_default12": estimate(te_unit, 1104, "36 N/T/T2 historical sessions, incl. 4 proposer calls", "12 independent streams x 46 sessions x 2 arms; stream, not session, is the inference unit."),
        "tokeneconomizer_all_configurations_default12": estimate(te_unit, 1656, "36 N/T/T2 historical sessions, incl. 4 proposer calls", "12 independent streams x 46 sessions x 3 arms; includes paid proposer."),
        "unpriced": {"authoring": None, "independent_review": None, "controller": None,
                     "tokeneconomizer_mechanical_grading_logical_tokens": 0,
                     "tokeneconomizer_harder_task_unit_cost": None,
                     "graphify_documents_visual_semantic_trials": None},
    }
    write("RERUN_ESTIMATES.json", estimates)
    print("Wrote ACCOUNTING.json and RERUN_ESTIMATES.json; no experiments or grading executed.")


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
