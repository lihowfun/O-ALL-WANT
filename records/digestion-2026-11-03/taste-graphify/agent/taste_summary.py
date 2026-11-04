"""Summarize an agent-level tasting: per-arm coverage, essential-correct questions, wrong claims, tokens,
tool calls and time, then apply the pre-registered rules in PREREG.md against the native arm N."""
import json
import statistics
import sys
from collections import defaultdict


def main(rows_path, grades_path, out_path):
    rows = [json.loads(line) for line in open(rows_path, encoding="utf-8")]
    grades = {g["key"]: g for g in (json.loads(line) for line in open(grades_path, encoding="utf-8"))}
    per = defaultdict(lambda: defaultdict(list))
    for row in rows:
        key = f"{row['arm']}|{row['id']}|{row['rep']}"
        grade = grades.get(key)
        if not grade:
            continue
        cell = per[row["arm"]][row["id"]]
        cell.append({"coverage": grade["coverage"], "essential_ok": grade["essential_ok"],
                     "wrong": grade["verdict"].get("wrong_claims") or 0, "contradicted": grade["contradicted"],
                     "tokens": row["tokens_total"], "tools": row["tool_calls"], "seconds": row["seconds"],
                     "cost": row.get("cost_usd") or 0.0, "bash": row["bash"]})
    summary = {}
    for arm, questions in per.items():
        q_cov = [statistics.mean(c["coverage"] for c in cells) for cells in questions.values()]
        q_ess = [statistics.mean(1.0 if c["essential_ok"] else 0.0 for c in cells) for cells in questions.values()]
        q_tok = [statistics.mean(c["tokens"] for c in cells) for cells in questions.values()]
        q_tools = [statistics.mean(c["tools"] for c in cells) for cells in questions.values()]
        q_sec = [statistics.mean(c["seconds"] for c in cells) for cells in questions.values()]
        summary[arm] = {
            "questions": len(questions), "runs": sum(len(c) for c in questions.values()),
            "coverage_mean": round(statistics.mean(q_cov), 3),
            "essential_ok_questions": round(sum(q_ess), 2),
            "wrong_claims": sum(c["wrong"] for cells in questions.values() for c in cells),
            "contradicted": sum(c["contradicted"] for cells in questions.values() for c in cells),
            "tokens_median": int(statistics.median(q_tok)), "tokens_total": int(sum(c["tokens"] for cells in questions.values() for c in cells)),
            "tool_calls_median": statistics.median(q_tools), "seconds_median": statistics.median(q_sec),
            "cost_usd_equiv": round(sum(c["cost"] for cells in questions.values() for c in cells), 2),
            "per_question": {qid: {"coverage": round(statistics.mean(c["coverage"] for c in cells), 3),
                                   "essential_ok": [c["essential_ok"] for c in cells],
                                   "tokens": [c["tokens"] for c in cells], "tools": [c["tools"] for c in cells]}
                             for qid, cells in sorted(questions.items())},
            "tool_commands_used": sum(1 for cells in questions.values() for c in cells for b in c["bash"]),
        }
    verdicts = {}
    base = summary.get("N")
    for arm, s in summary.items():
        if arm == "N" or not base:
            continue
        better = (s["coverage_mean"] >= base["coverage_mean"] + 0.10
                  or s["essential_ok_questions"] >= base["essential_ok_questions"] + 2)
        cheaper = (abs(s["coverage_mean"] - base["coverage_mean"]) < 0.05
                   and s["tokens_median"] < 0.7 * base["tokens_median"])
        verdicts[arm] = "understands better" if better else "same understanding, cheaper" if cheaper else \
            "not shown better than native"
    report = {"summary": summary, "verdicts_vs_N": verdicts}
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1)
    for arm in sorted(summary):
        s = summary[arm]
        print(f"{arm}: coverage {s['coverage_mean']} essential-ok {s['essential_ok_questions']}/{s['questions']} "
              f"wrong {s['wrong_claims']} tokens median {s['tokens_median']:,} total {s['tokens_total']:,} "
              f"tools median {s['tool_calls_median']} sec median {s['seconds_median']} tool cmds {s['tool_commands_used']}")
    print(verdicts)


if __name__ == "__main__":
    main(*sys.argv[1:4])
