"""V5 of PREREG.md: more seeds of the EGM self-test on the `events` case only, with the frozen runner's run_one.

  python3 v5_run.py <arms.json> <claude CLI> <out dir>

Plan (PREREG): repeat 3 in the frozen rotation (P, N, E), then N repeats 4-6. The food's spend so far (7,951,660,
RESULT.md of the self-test) counts against its D13 cap of 10M; a run starts only if the spend so far plus the
largest earlier run of that arm still fits (the repeat-3 group is checked as a whole, as in the frozen runner).
Exit codes follow the frozen runner: 3 budget guard, 4 billing, 5 plugin or run failure, 6 usage limit.
"""
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = os.path.join(HERE, "..", "..", "..", "digestion-2026-11-06", "egm-selftest")
PRIOR, CAP = 7_951_660, 10_000_000
LARGEST = {"N": 42_780, "E": 1_433_467, "P": 42_432}  # largest earlier run per arm (frozen rows.jsonl)
PLAN = [[("P", 3), ("N", 3), ("E", 3)], [("N", 4)], [("N", 5)], [("N", 6)]]


def main(arms_path, claude, out):
    spec = importlib.util.spec_from_file_location("frozen_egm_run", os.path.join(FROZEN, "taste_run.py"))
    tr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tr)
    arms = json.load(open(arms_path, encoding="utf-8"))
    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
    rows_path, dev_path = os.path.join(out, "rows.jsonl"), os.path.join(out, "deviations.jsonl")
    done, spent, largest = set(), 0, dict(LARGEST)
    if os.path.exists(rows_path):
        for line in open(rows_path, encoding="utf-8"):
            row = json.loads(line)
            done.add((row["arm"], row["rep"]))
            spent += row["tokens_total"]
            largest[row["arm"]] = max(largest[row["arm"]], row["tokens_total"])
    if os.path.exists(dev_path):
        spent += sum(json.loads(line).get("tokens_total", 0) for line in open(dev_path, encoding="utf-8"))
    for group in PLAN:
        todo = [(arm, rep) for arm, rep in group if (arm, rep) not in done]
        if not todo:
            continue
        need = sum(largest[arm] for arm, _rep in todo)
        if PRIOR + spent + need > CAP:
            print(f"budget guard: {PRIOR + spent:,} spent, next group about {need:,}; not starting {todo}", flush=True)
            return 3
        for arm, rep in todo:
            row = tr.run_one(arm, arms[arm], "events", rep, claude, out, 3600, "claude-opus-5-5", "high", "project")
            if row.get("usage_limited") or row["tokens_total"] == 0:
                spent += row["tokens_total"]
                with open(dev_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"key": f"{arm}|events|{rep}", "at": time.time(),
                                             "reason": "usage limit" if row.get("usage_limited") else "no tokens",
                                             "tokens_total": row["tokens_total"], "seconds": row["seconds"]}) + "\n")
                print(f"{arm} events r{rep}: cut by the usage limit; not a row; stopping (rerun to resume)", flush=True)
                return 6
            with open(rows_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            spent += row["tokens_total"]
            largest[arm] = max(largest[arm], row["tokens_total"])
            print(f"{arm} events r{rep}: exit {row['exit']} {row['seconds']}s agents {row['agent_calls']} report "
                  f"{row['report_found']} contamination {len(row['contamination'])} tokens {row['tokens_total']:,} "
                  f"(food total {PRIOR + spent:,})", flush=True)
            if row["api_key_source"] not in (None, "none"):
                return 4
            if arm == "E" and not (row["egm_command"] and "egm" in row["plugins"]):
                print("the EGM plugin did not load in arm E; stopping", flush=True)
                return 5
            if arm != "E" and "egm" in row["plugins"]:
                print(f"EGM loaded in arm {arm}; stopping", flush=True)
                return 5
            if row["exit"] not in (0, "timeout") and not row["report_found"]:
                return 5
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
