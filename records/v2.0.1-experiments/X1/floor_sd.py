"""Zero-spread floor for X1 (D32): pooled within-question SD of earlier repeated ERPNext runs, per model and grader.

Source runs: the 2026-11-06 codegraph tasting on ERPNext d9cb916 (arms N, G, S, C; questions q1-q4; 3 runs each),
Opus 5.5 grader in out-<cond>/grades.jsonl, Codex in validation/v4/<cond>/grades-codex-original.jsonl.
Every (arm, question) cell is used; a wrong-claim count of null (no answer) would be left out (there are none).

    python3 floor_sd.py <claude/oaw-2>/scripts/eval_stats.py floor_sd.json
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "..", "..")
SOURCES = {"opus": ("out-opus", "opus"), "haiku": ("out-haiku", "haiku")}


def main(eval_stats, out):
    spec = importlib.util.spec_from_file_location("eval_stats", eval_stats)
    es = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(es)
    result = {"floor_sd": {}, "sources": {}}
    for label, (folder, cond) in SOURCES.items():
        paths = {"opus": f"digestion-2026-11-06/taste-codegraph/{folder}/grades.jsonl",
                 "codex": f"digestion-2026-11-07/validation/v4/{cond}/grades-codex-original.jsonl"}
        result["floor_sd"][label] = {}
        for grader, rel in paths.items():
            cov, wrong = {}, {}
            for line in open(os.path.join(R, rel), encoding="utf-8"):
                g = json.loads(line)
                key = f"{g['arm']}|{g['id']}"
                cov.setdefault(key, []).append(g["coverage"])
                if g["verdict"].get("wrong_claims") is not None:
                    wrong.setdefault(key, []).append(g["verdict"]["wrong_claims"])
            result["floor_sd"][label][grader] = {"coverage": es.pooled_within_sd(cov), "wrong": es.pooled_within_sd(wrong),
                                                 "cells": len(cov), "runs": sum(len(v) for v in cov.values())}
            result["sources"][f"{label}/{grader}"] = rel
    json.dump(result, open(out, "w", encoding="utf-8"), indent=1)
    print(json.dumps(result["floor_sd"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
