"""X1 judgment (PREREG.md), computed only with OAW's scripts/eval_stats.py (D32).

Per model cell (opus, haiku) and per grader family (opus, codex):
  coverage      compare(M, N, margin 0.10, floor_sd = floor[cell][grader].coverage)
  wrong claims  compare(M, N, margin 0.5, lower is better, floor_sd = floor[cell][grader].wrong); no answer -> 0
  quality()     merges the two; agree() across the two families; lowest() across the cells.
Efficiency per cell: cost() on tool calls (pass when the 95% upper end < 0.8) or on tokens (pass when the upper
end < 1.0). Tool calls get +1 on every run of both arms only if some run has 0 calls (cost() needs counts > 0).
Decision (plan section 6, X1): every cell better or equivalent under both families and efficiency passes in every
cell -> default; no cell worse under both but something undetermined or efficiency fails -> optional; a cell worse
under both -> CLI only.

    python3 x1_judge.py --eval-stats <claude/oaw-2>/scripts/eval_stats.py --floor floor_sd.json \
        --cell opus=out-opus --cell haiku=out-haiku --out judge.json
Each cell folder holds rows.jsonl, grades-opus.jsonl and grades-codex.jsonl.
A cell with fewer than --min-questions complete pairs (budget stop) is computed and reported, but counts as
undetermined in the decision (PREREG: an incomplete cell can neither make the map a default nor demote it).
"""
import argparse
import importlib.util
import json
import os
import statistics
import sys


def load(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def per_arm(items, value):
    out = {"N": {}, "M": {}}
    for item in items:
        out[item["arm"]].setdefault(item["id"], []).append(value(item))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-stats", required=True)
    parser.add_argument("--floor", required=True)
    parser.add_argument("--cell", action="append", required=True, help="label=folder")
    parser.add_argument("--out", required=True)
    parser.add_argument("--min-questions", type=int, default=12)
    args = parser.parse_args(argv)
    spec = importlib.util.spec_from_file_location("eval_stats", args.eval_stats)
    es = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(es)
    floor = json.load(open(args.floor, encoding="utf-8"))["floor_sd"]
    report = {"cells": {}}
    agreed = []
    efficiency_all = True
    for cell in args.cell:
        label, folder = cell.split("=", 1)
        rows = load(os.path.join(folder, "rows.jsonl"))
        both = {q for q in {r["id"] for r in rows} if {("N", q), ("M", q)} <= {(r["arm"], r["id"]) for r in rows}}
        rows = [r for r in rows if r["id"] in both]
        result = {"questions": sorted(both), "graders": {}}
        classes = {}
        for grader in ("opus", "codex"):
            grades = [g for g in load(os.path.join(folder, f"grades-{grader}.jsonl")) if g["id"] in both]
            keys = {(g["arm"], g["id"]) for g in grades}
            if keys != {(r["arm"], r["id"]) for r in rows}:
                raise SystemExit(f"{label}/{grader}: grades do not cover every answer")
            cov = per_arm(grades, lambda g: g["coverage"])
            wrong = per_arm(grades, lambda g: g["verdict"].get("wrong_claims") or 0)
            fl = floor[label][grader]
            c = es.compare(cov["M"], cov["N"], 0.10, floor_sd=fl["coverage"])
            w = es.compare(wrong["M"], wrong["N"], 0.5, lower_is_better=True, floor_sd=fl["wrong"])
            q = es.quality(c["class"], w["class"])
            classes[grader] = q
            result["graders"][grader] = {
                "coverage": {k: c[k] for k in ("point", "ci95", "ci90", "se", "floor_applied", "class", "mde")},
                "coverage_mean": {a: statistics.fmean(v[0] for v in cov[a].values()) for a in ("N", "M")},
                "wrong": {k: w[k] for k in ("point", "ci95", "ci90", "se", "floor_applied", "class", "mde")},
                "wrong_total": {a: sum(v[0] for v in wrong[a].values()) for a in ("N", "M")},
                "essential_ok": {a: sum(1 for g in grades if g["arm"] == a and g["essential_ok"]) for a in ("N", "M")},
                "quality": q,
                "per_question": {qid: {a: [cov[a][qid][0], wrong[a][qid][0]] for a in ("N", "M")}
                                 for qid in sorted(both)}}
        result["quality"] = es.agree(classes["opus"], classes["codex"])
        result["complete"] = len(both) >= args.min_questions
        agreed.append(result["quality"] if result["complete"] else "undetermined")
        tools = per_arm(rows, lambda r: r["tool_calls"])
        shift = 1 if any(v[0] == 0 for arm in tools.values() for v in arm.values()) else 0
        if shift:
            tools = {a: {q: [v[0] + 1] for q, v in d.items()} for a, d in tools.items()}
        tokens = per_arm(rows, lambda r: r["tokens_total"])
        seconds = per_arm(rows, lambda r: r["seconds"])
        tc, tk, sec = es.cost(tools["M"], tools["N"]), es.cost(tokens["M"], tokens["N"]), es.cost(seconds["M"], seconds["N"])
        passes = tc["ci95"][1] < 0.8 or tk["ci95"][1] < 1.0
        efficiency_all = efficiency_all and passes
        result["efficiency"] = {"tool_calls": {k: tc[k] for k in ("ratio", "ci95", "class")}, "tool_call_shift": shift,
                                "tokens": {k: tk[k] for k in ("ratio", "ci95", "class")},
                                "seconds": {k: sec[k] for k in ("ratio", "ci95", "class")}, "passes": passes,
                                "totals": {a: {"tool_calls": sum(r["tool_calls"] for r in rows if r["arm"] == a),
                                               "tokens": sum(r["tokens_total"] for r in rows if r["arm"] == a)}
                                           for a in ("N", "M")}}
        m_rows = [r for r in rows if r["arm"] == "M"]
        result["map_use"] = {"runs": len(m_rows),
                             "skill_invoked": sum(1 for r in m_rows if r.get("skill_calls")),
                             "code_index_run": sum(1 for r in m_rows if r.get("map_commands")),
                             "code_index_commands": sum(r.get("map_commands", 0) for r in m_rows)}
        result["judgment"] = es.judgment(result["quality"], tk, grading="cross-family", conditions=1,
                                         basis=f"X1 ERPNext, {label}")
        report["cells"][label] = result
    overall = es.lowest(*agreed)
    if all(q in ("better", "equivalent") for q in agreed) and efficiency_all:
        decision = "default"
    elif "worse" in agreed:
        decision = "cli-only"
    else:
        decision = "optional"
    report.update({"quality_lowest": overall, "efficiency_all_cells": efficiency_all, "decision": decision})
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    for label, result in report["cells"].items():
        print(label, result["quality"], {g: v["quality"] for g, v in result["graders"].items()},
              "tools", round(result["efficiency"]["tool_calls"]["ratio"], 3),
              [round(x, 3) for x in result["efficiency"]["tool_calls"]["ci95"]],
              "tokens", round(result["efficiency"]["tokens"]["ratio"], 3),
              [round(x, 3) for x in result["efficiency"]["tokens"]["ci95"]], "map", result["map_use"])
    print("decision:", decision, "| quality lowest:", overall, "| efficiency all cells:", efficiency_all)
    return 0


if __name__ == "__main__":
    sys.exit(main())
