"""Summary and pre-registered verdict for the TokenEconomizer session-stream tasting (PREREG.md).

    python3 summarize.py <out dir> <food ledger.jsonl> <records dir> <tasting dir prefix to mask>

Reads the runner's rows.jsonl and the food's own ledger (joined by session id), writes to the records dir:
rows.jsonl (local paths masked), grades.jsonl (the mechanical grades), summary.json (per-arm, per-pair,
early/late, mechanism activity and the verdict by the rules written before the run).
"""
import json
import math
import os
import sys

LATE_FROM = 7          # positions 7-12 are the late half
PLUG_IN_RATIO = 0.85   # rule 4
DECLINE_RATIO = 1.15   # rule 6


def cost(row):
    return float(row["effective_tokens"]) + float(row.get("sidecall_effective_tokens") or 0)


def correct(row):
    grade = row["grade"]
    return bool(grade["hidden_pass"]) and not grade["suite_failed_other"]


def mask(value, prefix):
    if isinstance(value, str):
        return value.replace(prefix, "<T>")
    if isinstance(value, list):
        return [mask(v, prefix) for v in value]
    if isinstance(value, dict):
        return {k: mask(v, prefix) for k, v in value.items()}
    return value


def main():
    out_dir, ledger_path, records, prefix = sys.argv[1:5]
    rows = [json.loads(line) for line in open(os.path.join(out_dir, "rows.jsonl"), encoding="utf-8")]
    ledger = [json.loads(line) for line in open(ledger_path, encoding="utf-8")] if os.path.exists(ledger_path) else []
    sessions = {r["session_id"]: r for r in ledger if r.get("kind") == "session"}
    overhead_records = [r for r in ledger if r.get("kind") == "overhead"]

    with open(os.path.join(records, "rows.jsonl"), "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(mask(row, prefix), ensure_ascii=False) + "\n")
    with open(os.path.join(records, "grades.jsonl"), "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps({"arm": row["arm"], "id": row["id"], "position": row["position"],
                                     "hidden_pass": row["grade"]["hidden_pass"],
                                     "suite_failed_other": row["grade"]["suite_failed_other"],
                                     "suite_tail": row["grade"]["suite_tail"], "correct": correct(row),
                                     "grader": "mechanical: hidden pytest + whole suite, arm-blind"}) + "\n")

    by = {(r["arm"], r["id"]): r for r in rows}
    ids = sorted({r["id"] for r in rows}, key=lambda i: min(r["position"] for r in rows if r["id"] == i))
    pairs = []
    for task_id in ids:
        n, t = by.get(("N", task_id)), by.get(("T", task_id))
        if not (n and t):
            continue
        led = sessions.get(t["session_id"]) or {}
        overhead = led.get("overhead") or {}
        activity = {
            "facts_injected_chars": int(led.get("injected_chars") or 0),
            "deny_list_applied": led.get("untool_applied") or [],
            "tools_loaded_T": len(t.get("tools_loaded") or []), "tools_loaded_N": len(n.get("tools_loaded") or []),
            "nudges": int(led.get("nudges") or 0), "aborts": int(led.get("aborts") or 0),
            "judge_tokens": overhead.get("spiral_judge_tokens"), "proposer_tokens": overhead.get("optimizer_tokens"),
            "hook_messages": len(t.get("hook_messages") or []), "ledger_found": bool(led)}
        activity["microskills_acted"] = activity["facts_injected_chars"] > 0
        # In effect during the session: fewer tools loaded than N. The ledger's list is the one at fold time.
        activity["toolprune_acted"] = activity["tools_loaded_T"] < activity["tools_loaded_N"]
        activity["loopguard_acted"] = activity["nudges"] > 0 or activity["aborts"] > 0
        pairs.append({"id": task_id, "position": t["position"],
                      "N": {"cost": cost(n), "tokens_total": n["tokens_total"], "turns": n["turns"],
                            "tool_calls": n["tool_calls"], "test_runs": n["test_runs"], "correct": correct(n),
                            "cost_usd": n.get("cost_usd"), "seconds": n["seconds"], "hit_turn_limit": n["hit_turn_limit"]},
                      "T": {"cost": cost(t), "tokens_total": t["tokens_total"] + t.get("sidecall_tokens_total", 0),
                            "session_tokens_total": t["tokens_total"], "sidecall_tokens_total": t.get("sidecall_tokens_total", 0),
                            "sidecall_effective_tokens": t.get("sidecall_effective_tokens", 0), "sidecalls": len(t.get("sidecalls") or []),
                            "turns": t["turns"], "tool_calls": t["tool_calls"], "test_runs": t["test_runs"], "correct": correct(t),
                            "cost_usd": (t.get("cost_usd") or 0) + (t.get("sidecall_cost_usd") or 0), "seconds": t["seconds"],
                            "hit_turn_limit": t["hit_turn_limit"], "food": activity},
                      "ratio": round(cost(t) / cost(n), 4) if cost(n) else None})

    def half(selected):
        n_cost = sum(p["N"]["cost"] for p in selected)
        t_cost = sum(p["T"]["cost"] for p in selected)
        t_session = sum(p["T"]["cost"] - p["T"]["sidecall_effective_tokens"] for p in selected)
        return {"pairs": len(selected), "N_cost": round(n_cost, 1), "T_cost": round(t_cost, 1),
                "T_cost_without_food_calls": round(t_session, 1),
                "ratio_without_food_calls": round(t_session / n_cost, 4) if n_cost else None,
                "N_turns": sum(p["N"]["turns"] for p in selected), "T_turns": sum(p["T"]["turns"] for p in selected),
                "N_raw_tokens": sum(p["N"]["tokens_total"] for p in selected),
                "T_raw_tokens": sum(p["T"]["tokens_total"] for p in selected),
                "ratio": round(t_cost / n_cost, 4) if n_cost else None,
                "T_cheaper_pairs": sum(1 for p in selected if p["T"]["cost"] < p["N"]["cost"])}

    early = half([p for p in pairs if p["position"] < LATE_FROM])
    late_pairs = [p for p in pairs if p["position"] >= LATE_FROM]
    late = half(late_pairs)
    q_n = sum(1 for p in pairs if p["N"]["correct"])
    q_t = sum(1 for p in pairs if p["T"]["correct"])
    acted = {m: sum(1 for p in late_pairs if p["T"]["food"][m + "_acted"]) for m in ("microskills", "toolprune", "loopguard")}
    raw_total = sum(r["tokens_total"] + r.get("sidecall_tokens_total", 0) for r in rows)
    side_eff = sum(float(r.get("sidecall_effective_tokens") or 0) for r in rows if r["arm"] == "T")
    t_eff = sum(cost(r) for r in rows if r["arm"] == "T")

    # Pre-registered rules, in order.
    if late["pairs"] < 3:
        verdict, why = "no-verdict", f"only {late['pairs']} late pairs completed (needs 3)"
    elif not any(acted.values()):
        verdict, why = "not-shown-better", "vacuous: none of the food's mechanisms acted in a late session"
    elif q_t <= q_n - 2:
        verdict, why = "decline", f"quality fell: T {q_t} correct vs N {q_n}"
    elif (q_t >= q_n - 1 and late["ratio"] <= PLUG_IN_RATIO
          and late["T_cheaper_pairs"] >= math.ceil(2 * late["pairs"] / 3)):
        single = [m for m, k in acted.items() if k]
        paid = {"microskills": True, "toolprune": False, "loopguard": True}
        if len(single) == 1 and not paid[single[0]]:
            verdict, why = "absorb", f"saving with only {single[0]} acting, which needs no paid call"
        else:
            verdict, why = "plug-in", "late cost ratio and pair wins pass with quality held"
    elif late["ratio"] >= DECLINE_RATIO:
        verdict, why = "decline", f"late cost ratio {late['ratio']} >= {DECLINE_RATIO}"
    else:
        verdict, why = "not-shown-better", "late saving below the pre-registered bar or not consistent across pairs"

    summary = {"pairs": pairs, "early": early, "late": late, "quality": {"N_correct": q_n, "T_correct": q_t, "pairs": len(pairs)},
               "late_mechanism_sessions": acted, "food_overhead_effective_tokens": round(side_eff, 1),
               "food_overhead_share_of_T": round(side_eff / t_eff, 4) if t_eff else None,
               "food_overhead_records_in_ledger": len(overhead_records),
               "raw_tokens_total_all_arms": raw_total, "verdict": verdict, "why": why,
               "rules": "PREREG.md, 'judgement rules' 1-7"}
    json.dump(summary, open(os.path.join(records, "summary.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: summary[k] for k in ("early", "late", "quality", "late_mechanism_sessions",
                                                "food_overhead_share_of_T", "raw_tokens_total_all_arms", "verdict", "why")},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
