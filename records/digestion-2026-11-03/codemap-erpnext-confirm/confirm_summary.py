"""Summarize the code-map confirmation on ERPNext and apply the rules frozen in PREREG.md.

  python3 confirm_summary.py <rows.jsonl> <grades.jsonl> <summary.json>

Per arm: coverage (mean over questions of the mean over repeats), runs with every essential fact, wrong claims,
tokens and tool calls (median over questions of the mean over repeats), turn-cap cut-offs, and the spread between
repeats. Each map arm (S, G) is then judged against the native arm N.
"""
import json
import statistics
import sys
from collections import defaultdict


def describe(rows, grades):
    per = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grade = grades.get(f"{row['arm']}|{row['id']}|{row['rep']}")
        if not grade:
            continue
        per[row["arm"]][row["id"]].append({
            "coverage": grade["coverage"], "essential_ok": grade["essential_ok"],
            "wrong": grade["verdict"].get("wrong_claims") or 0, "contradicted": grade["contradicted"],
            "tokens": row["tokens_total"], "tools": row["tool_calls"], "turns": row.get("turns") or 0,
            "seconds": row["seconds"], "cut": bool(row.get("hit_turn_limit")), "rep": row["rep"]})
    summary = {}
    for arm, questions in per.items():
        q = {qid: {
            "coverage": statistics.mean(c["coverage"] for c in cells),
            "coverage_min": min(c["coverage"] for c in cells), "coverage_max": max(c["coverage"] for c in cells),
            "tokens": statistics.mean(c["tokens"] for c in cells), "tools": statistics.mean(c["tools"] for c in cells),
            "runs": len(cells)} for qid, cells in sorted(questions.items())}
        runs = [c for cells in questions.values() for c in cells]
        summary[arm] = {
            "questions": len(q), "runs": len(runs),
            "coverage_mean": round(statistics.mean(v["coverage"] for v in q.values()), 3),
            "essential_ok_runs": sum(1 for c in runs if c["essential_ok"]),
            "wrong_claims": sum(c["wrong"] for c in runs),
            "contradicted": sum(c["contradicted"] for c in runs),
            "cutoffs": sum(1 for c in runs if c["cut"]),
            "tokens_median": int(statistics.median(v["tokens"] for v in q.values())),
            "tokens_total": sum(c["tokens"] for c in runs),
            "tool_calls_median": round(statistics.median(v["tools"] for v in q.values()), 2),
            "turns_median": statistics.median(c["turns"] for c in runs),
            "seconds_median": statistics.median(c["seconds"] for c in runs),
            "repeat_spread": round(statistics.mean(v["coverage_max"] - v["coverage_min"] for v in q.values()), 3),
            "per_question": {qid: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in item.items()}
                             for qid, item in q.items()},
        }
    return summary


def judge(x, n):
    """Rules frozen in PREREG.md, map arm x against native n (same condition)."""
    shared = sorted(set(x["per_question"]) & set(n["per_question"]))
    dcov = x["coverage_mean"] - n["coverage_mean"]
    not_lower = sum(1 for q in shared if x["per_question"][q]["coverage"] >= n["per_question"][q]["coverage"])
    worse = (dcov <= -0.10 or x["wrong_claims"] >= n["wrong_claims"] + 3 or x["cutoffs"] >= n["cutoffs"] + 3)
    better = ((dcov >= 0.10 and not_lower >= 3) or x["essential_ok_runs"] >= n["essential_ok_runs"] + 3)
    saving = []
    for metric, median in (("tokens", "tokens_median"), ("tools", "tool_calls_median")):
        if x[median] <= 0.70 * n[median]:
            lower_on = sum(1 for q in shared if x["per_question"][q][metric] < n["per_question"][q][metric])
            if lower_on >= 3:
                saving.append(metric)
    cheaper = dcov >= -0.05 and x["wrong_claims"] <= n["wrong_claims"] and bool(saving)
    if worse:
        verdict = "worse than native"
    elif better:
        verdict = "understands better"
    elif cheaper:
        verdict = "same understanding, cheaper (" + ", ".join(saving) + ")"
    else:
        verdict = "not shown better than native"
    return {"verdict": verdict, "coverage_delta": round(dcov, 3), "questions_not_lower": not_lower,
            "tokens_ratio": round(x["tokens_median"] / n["tokens_median"], 3) if n["tokens_median"] else None,
            "tools_ratio": round(x["tool_calls_median"] / n["tool_calls_median"], 3) if n["tool_calls_median"] else None}


def main(rows_path, grades_path, out_path):
    rows = [json.loads(line) for line in open(rows_path, encoding="utf-8")]
    grades = {g["key"]: g for g in (json.loads(line) for line in open(grades_path, encoding="utf-8"))}
    summary = describe(rows, grades)
    verdicts = {arm: judge(s, summary["N"]) for arm, s in summary.items() if arm != "N" and "N" in summary}
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({"summary": summary, "verdicts_vs_N": verdicts}, handle, ensure_ascii=False, indent=1)
    for arm in sorted(summary):
        s = summary[arm]
        print(f"{arm}: runs {s['runs']} coverage {s['coverage_mean']} essential-ok runs {s['essential_ok_runs']} "
              f"wrong {s['wrong_claims']} cutoffs {s['cutoffs']} tokens median {s['tokens_median']:,} "
              f"total {s['tokens_total']:,} tools median {s['tool_calls_median']} turns median {s['turns_median']} "
              f"repeat spread {s['repeat_spread']}")
    for arm, v in verdicts.items():
        print(arm, v)


if __name__ == "__main__":
    main(*sys.argv[1:4])
