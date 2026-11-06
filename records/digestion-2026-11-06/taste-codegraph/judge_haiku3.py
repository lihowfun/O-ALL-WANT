"""ADDENDUM-HAIKU3.md: judge codegraph's Haiku condition with grading A and B, then D29 over four conditions.

  python3 judge_haiku3.py <rows.jsonl> <grades.jsonl> <grades-b.jsonl> <out.json>

Quality per grading (the confirmation's thresholds): worse if coverage is 0.10 lower, or wrong claims 3 more, or
cut-offs 3 more; better if coverage is 0.10 higher with at least 3 of 4 questions not lower, or the rate of runs
with every essential fact is 0.25 higher. A direction counts only if A and B agree; otherwise "same".
The other three conditions are taken from the ledger (quality same, token ratios 1.200, 1.308, 1.722).
"""
import json
import sys

from summary import describe

OTHERS = {"opus-5-5": ("same", 1.200), "sonnet-5-5": ("same", 1.308), "opus-4-8": ("same", 1.722)}
CAP = 1.5


def quality(x, n):
    shared = sorted(set(x["per_question"]) & set(n["per_question"]))
    dcov = x["coverage_mean"] - n["coverage_mean"]
    not_lower = sum(1 for q in shared if x["per_question"][q]["coverage"] >= n["per_question"][q]["coverage"])
    rate = lambda s: s["essential_ok_runs"] / s["runs"] if s["runs"] else 0.0
    if dcov <= -0.10 or x["wrong_claims"] >= n["wrong_claims"] + 3 or x["cutoffs"] >= n["cutoffs"] + 3:
        return "worse"
    if (dcov >= 0.10 and not_lower >= 3) or rate(x) >= rate(n) + 0.25:
        return "better"
    return "same"


def outcome(q, cost):
    if q == "worse":
        return "excrete"
    if q == "better":
        return "default" if cost <= CAP else "optional"
    return "optional" if cost <= CAP else "excrete"


def main(rows_path, a_path, b_path, out_path):
    rows = [json.loads(line) for line in open(rows_path, encoding="utf-8")]
    result = {}
    for name, path in (("A", a_path), ("B", b_path)):
        grades = {g["key"]: g for g in (json.loads(line) for line in open(path, encoding="utf-8"))}
        not_run = [k for k, g in grades.items() if not g["verdict"].get("_grader_tokens")]
        if not_run:
            raise SystemExit(f"grading {name} has {len(not_run)} grades that did not run: {not_run[:5]}")
        s = describe(rows, grades)
        result[name] = {"summary": {arm: {k: s[arm][k] for k in ("runs", "coverage_mean", "essential_ok_runs",
                                                                 "wrong_claims", "tokens_median", "tool_calls_median")}
                                    for arm in s},
                        "quality_C": quality(s["C"], s["N"]), "quality_G": quality(s["G"], s["N"]),
                        "quality_S": quality(s["S"], s["N"])}
    sa = describe(rows, {g["key"]: g for g in (json.loads(l) for l in open(a_path, encoding="utf-8"))})
    cost = round(sa["C"]["tokens_median"] / sa["N"]["tokens_median"], 3)
    qa, qb = result["A"]["quality_C"], result["B"]["quality_C"]
    haiku_q = qa if qa == qb else "same"
    conditions = dict(OTHERS, **{"haiku-5-5": (haiku_q, cost)})
    order = {"excrete": 0, "optional": 1, "default": 2}
    per = {c: outcome(q, r) for c, (q, r) in conditions.items()}
    deciding = min(per, key=lambda c: (order[per[c]], -conditions[c][1]))
    result["haiku"] = {"quality_A": qa, "quality_B": qb, "quality": haiku_q, "cost_ratio": cost}
    result["d29"] = {"per_condition": {c: {"quality": q, "cost_ratio": r, "outcome": per[c]} for c, (q, r) in conditions.items()},
                     "deciding_condition": deciding, "outcome": per[deciding],
                     "quality": conditions[deciding][0], "cost_ratio": conditions[deciding][1]}
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1)
    print(json.dumps({"haiku": result["haiku"], "d29": result["d29"]}, ensure_ascii=False, indent=1))
    for name in ("A", "B"):
        print(name, {arm: (v["coverage_mean"], v["essential_ok_runs"], v["wrong_claims"], v["tokens_median"])
                     for arm, v in result[name]["summary"].items()})


if __name__ == "__main__":
    main(*sys.argv[1:5])
