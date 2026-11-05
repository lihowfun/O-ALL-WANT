"""Summary and the pre-registered decision rules (PREREG.md) for the court-skill tasting.

    python3 taste_summary.py rows.jsonl grades.jsonl summary.json
"""
import json
import statistics
import sys


def main(rows_path, grades_path, out_path):
    rows = [json.loads(line) for line in open(rows_path, encoding="utf-8")]
    grades = {g["key"]: g for g in (json.loads(line) for line in open(grades_path, encoding="utf-8"))}
    arms = {}
    for row in rows:
        grade = grades.get(f"{row['arm']}|{row['id']}|{row['rep']}")
        if not grade:
            continue
        a = arms.setdefault(row["arm"], {"cases": {}, "tokens": [], "seconds": [], "words": [], "agents": []})
        v = grade["verdict"]
        a["cases"][row["id"]] = {"coverage": grade["coverage"], "essential_ok": grade["essential_ok"],
                                 "bottom_line": v.get("bottom_line"), "bottom_line_ok": grade["bottom_line_ok"],
                                 "false_alarms_raised": grade["false_alarms_raised"],
                                 "wrong_claims": v.get("wrong_claims"), "unearned_praise": v.get("unearned_praise"),
                                 "contradicted": grade["contradicted"], "tokens": row["tokens_total"],
                                 "words": row["answer_words"], "agent_calls": row["agent_calls"],
                                 "court_tally": row.get("court_tally")}
        a["tokens"].append(row["tokens_total"])
        a["seconds"].append(row["seconds"])
        a["words"].append(row["answer_words"])
        a["agents"].append(row["agent_calls"])
    summary = {}
    for arm, a in arms.items():
        cs = a["cases"].values()
        summary[arm] = {"n": len(a["cases"]),
                        "coverage": round(statistics.mean(c["coverage"] for c in cs), 3),
                        "essential_ok": sum(c["essential_ok"] for c in cs),
                        "bottom_line_ok": sum(c["bottom_line_ok"] for c in cs),
                        "false_alarms": sum(c["false_alarms_raised"] for c in cs),
                        "wrong_claims": sum(c["wrong_claims"] or 0 for c in cs),
                        "unearned_praise": sum(c["unearned_praise"] or 0 for c in cs),
                        "tokens_median": statistics.median(a["tokens"]), "tokens_total": sum(a["tokens"]),
                        "seconds_median": statistics.median(a["seconds"]), "words_median": statistics.median(a["words"]),
                        "agent_calls_median": statistics.median(a["agents"]), "cases": a["cases"]}
    rules = {}
    if "N" in summary:
        flawed = [cid for cid, c in summary["N"]["cases"].items() if cid in ("c1", "c2", "c3")]
        go = sum(1 for cid in flawed if summary["N"]["cases"][cid]["bottom_line"] == "go")
        rules["R0_premise_plain_ask_agrees"] = go >= 2
        rules["R0_N_go_on_flawed"] = go
    if "C" in summary and "P" in summary:
        c, p = summary["C"], summary["P"]
        adds = ((c["coverage"] >= p["coverage"] + 0.10 or c["essential_ok"] >= p["essential_ok"] + 2)
                and c["bottom_line_ok"] >= p["bottom_line_ok"] and c["false_alarms"] <= p["false_alarms"] + 2)
        redundant = p["coverage"] >= c["coverage"] - 0.05 and p["bottom_line_ok"] >= c["bottom_line_ok"]
        rules["R1_court_adds_over_native_ask"] = adds
        rules["R2_redundant_native_ask_matches"] = redundant and not adds
        rules["R3_not_shown_better"] = not adds and not redundant
        rules["token_ratio_C_over_P_median"] = round(c["tokens_median"] / max(p["tokens_median"], 1), 1)
    if "C" in summary and "N" in summary:
        c, n = summary["C"], summary["N"]
        rules["info_C_vs_N_adds"] = ((c["coverage"] >= n["coverage"] + 0.10 or c["essential_ok"] >= n["essential_ok"] + 2)
                                     and c["bottom_line_ok"] >= n["bottom_line_ok"])
    result = {"arms": summary, "rules": rules}
    json.dump(result, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for arm, s in summary.items():
        print(arm, {k: v for k, v in s.items() if k != "cases"})
    print(rules)


if __name__ == "__main__":
    main(*sys.argv[1:4])
