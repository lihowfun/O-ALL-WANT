"""Zero-spread floors for X2 (PREREG.md): pooled within-(arm, case) SD of the detection rate and of the unsupported
claim count, from the repeated Opus 5.5 reviews of the EGM self-test (3 runs) and V5 (events, more runs), one
value per grader family. No repeated Codex reviews exist, so the Codex cell uses the same floors.

    python3 x2_floor.py <eval_stats.py> > floor.json
"""
import importlib.util
import json
import os
import sys

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
SOURCES = {
    "opus": ["digestion-2026-11-06/egm-selftest/out/grades.jsonl", "digestion-2026-11-07/validation/v5/out/grades-opus.jsonl"],
    "codex": ["digestion-2026-11-07/validation/v4/egm/grades-codex-original.jsonl",
              "digestion-2026-11-07/validation/v5/out/grades-codex-original.jsonl"],
}
PLANTED = {"orders": 4, "events": 4}


def main(stats_path):
    spec = importlib.util.spec_from_file_location("eval_stats", stats_path)
    stats = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stats)
    result = {}
    for family, paths in SOURCES.items():
        det, unsup = {}, {}
        for rel in paths:
            for line in open(os.path.join(R, rel), encoding="utf-8"):
                row = json.loads(line)
                cell = (row["arm"], row["id"])
                if row["id"] in PLANTED:
                    det.setdefault(cell, []).append(len(row["detected"]) / PLANTED[row["id"]])
                unsup.setdefault(cell, []).append(row["unsupported"])
        result[family] = {"detection": stats.pooled_within_sd(det), "unsupported": stats.pooled_within_sd(unsup),
                          "cells": len(unsup), "reports": sum(len(v) for v in unsup.values())}
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
