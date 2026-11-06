"""Summarize the EGM self-test and apply the rules frozen in PREREG.md.

  python3 summary.py <rows.jsonl> <grades.jsonl> <summary.json>

Only (case, repeat) groups in which every arm has a graded row are compared. Per arm: planted detections
(critical, major) out of the planted total, unsupported concrete claims, clean-case false alarms, valid reviews,
tokens (median per run and total), sub-agents, seconds, changed pristine files and N/P contamination. E and P
are each judged against N twice: by the current tasting rules and by the D21 tier-B wording.
"""
import json
import statistics
import sys
from collections import defaultdict

PLANTED = {"orders": 4, "events": 4, "clean": 0}


def main(rows_path, grades_path, out_path):
    rows = {(r["arm"], r["id"], r["rep"]): r for r in (json.loads(l) for l in open(rows_path, encoding="utf-8"))}
    grades = {(g["arm"], g["id"], g["rep"]): g for g in (json.loads(l) for l in open(grades_path, encoding="utf-8"))}
    arms = sorted({k[0] for k in rows})
    groups = sorted({(k[1], k[2]) for k in rows if all((a, k[1], k[2]) in grades for a in arms)})
    summary = {}
    for arm in arms:
        cells = [(rows[(arm, c, r)], grades[(arm, c, r)]) for c, r in groups]
        tokens = [row["tokens_total"] for row, _g in cells]
        summary[arm] = {
            "runs": len(cells),
            "planted_total": sum(PLANTED[row["id"]] for row, _g in cells),
            "detections": sum(len(g["detected"]) for _r, g in cells),
            "critical": sum(g["critical"] for _r, g in cells),
            "major": sum(g["major"] for _r, g in cells),
            "unsupported": sum(g["unsupported"] for _r, g in cells),
            "clean_false_alarms": sum(g["unsupported"] for row, g in cells if row["id"] == "clean"),
            "valid_reviews": sum(1 for _r, g in cells if g["valid"]),
            "reports_found": sum(1 for row, _g in cells if row["report_found"]),
            "tokens_median": int(statistics.median(tokens)) if tokens else 0,
            "tokens_total": sum(tokens),
            "agent_calls_total": sum(row["agent_calls"] + row["agent_calls_nested"] for row, _g in cells),
            "seconds_median": statistics.median(row["seconds"] for row, _g in cells) if cells else 0,
            "mutated_runs": sum(1 for row, _g in cells if row["mutated"] or row["missing"]),
            "contaminated_runs": sum(1 for row, _g in cells if row["contamination"]),
            "per_case": {case: {"detections": sum(len(grades[(arm, c, r)]["detected"]) for c, r in groups if c == case),
                                "unsupported": sum(grades[(arm, c, r)]["unsupported"] for c, r in groups if c == case),
                                "runs": sum(1 for c, _r in groups if c == case)}
                         for case in PLANTED},
        }
    verdicts = {}
    n = summary.get("N")
    if n:
        for arm in arms:
            if arm == "N":
                continue
            x = summary[arm]
            worse = x["detections"] <= n["detections"] - 2 or x["unsupported"] >= n["unsupported"] + 3
            better = ((x["detections"] >= n["detections"] + 2 and x["critical"] >= n["critical"])
                      or (x["unsupported"] <= n["unsupported"] - 3 and x["detections"] >= n["detections"]))
            cheaper = (x["detections"] >= n["detections"] and x["unsupported"] <= n["unsupported"]
                       and x["tokens_median"] <= 0.70 * n["tokens_median"])
            verdict = ("worse than native" if worse else "better than native" if better else
                       "same quality, cheaper" if cheaper else "not shown better than native")
            parity = x["detections"] >= n["detections"] and x["unsupported"] <= n["unsupported"]
            verdicts[arm] = {
                "verdict": verdict,
                "current_tasting_rules": "absorb" if (better or cheaper) else ("decline" if worse else "not-shown-better"),
                "d21_tier_b": "ships (parity or better)" if parity and not worse else "does not ship",
                "detections_delta": x["detections"] - n["detections"],
                "unsupported_delta": x["unsupported"] - n["unsupported"],
                "tokens_median_ratio": round(x["tokens_median"] / n["tokens_median"], 3) if n["tokens_median"] else None,
            }
    ceiling = None
    if n:
        ceiling = {"native_detections": n["detections"], "planted_total": n["planted_total"],
                   "quality_axis_can_show_better": n["detections"] < n["planted_total"] - 1}
    result = {"groups_compared": [f"{c} r{r}" for c, r in groups], "summary": summary, "verdicts_vs_N": verdicts,
              "ceiling": ceiling}
    json.dump(result, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for arm in arms:
        s = summary[arm]
        print(f"{arm}: runs {s['runs']} detections {s['detections']}/{s['planted_total']} (critical {s['critical']}, "
              f"major {s['major']}) unsupported {s['unsupported']} clean false alarms {s['clean_false_alarms']} "
              f"valid {s['valid_reviews']} tokens median {s['tokens_median']:,} total {s['tokens_total']:,} "
              f"agents {s['agent_calls_total']} mutated {s['mutated_runs']} contaminated {s['contaminated_runs']}")
    for arm, v in verdicts.items():
        print(arm, v)
    print("ceiling", ceiling)


if __name__ == "__main__":
    main(*sys.argv[1:4])
