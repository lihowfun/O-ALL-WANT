#!/usr/bin/env python3
"""cap_judge: the verdict of the capability tasting from the counted rows (capability/PLAN.md sections 6 and 7).

Per cell and task, from whether N1, N2 and the candidate S passed:
  new pass     S passed, N1 and N2 did not
  regression   S did not pass, N1 and N2 did
  missed       S did not pass, exactly one of N1 and N2 did
Per cell: improved (at least 2 new passes, no regression, no miss), worse (at least 2 regressions), else undecided.

Idle check, per cell and idle task, S paired with N:
  fail        S's startup tokens exceed N's by more than 2%, or in both cells N solved this task and S did not
  undecided   only one cell has N solved and S not; neither solved it; or a record the rule needs is missing
  pass        otherwise
A candidate's idle result is fail if any pair fails, undecided if any is undecided, pass otherwise.

Per candidate, the first line that applies:
  1  not completed   the install failed, or any required run or idle run is missing
  2  not adopted     a cell is worse, or the idle result is fail
  3  optional        a cell improved, no cell has a regression or a miss, and the idle result is pass
  4  below the bar   everything else (including an undecided idle result)

usage: cap_judge.py <state folder> [<out.json>]
"""
import json
import os
import sys

CELLS = ("claude", "codex")
CANDIDATES = ("P1", "P2", "P3")
IDLE_RATIO = 1.02
VERDICTS = {"not completed": "未完成，不判", "not adopted": "本輪不採用", "optional": "暫列可選用",
            "below the bar": "本輪未達推薦門檻"}


def read_rows(path):
    if not os.path.exists(path):
        return []
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def index(rows):
    """(unit, arm) -> row; a second row for the same key is an error (a first counted result is never replaced)."""
    out = {}
    for row in rows:
        key = (row["unit"], row["arm"])
        if key in out:
            raise SystemExit(f"two counted rows for {key}")
        out[key] = row
    return out


def cell_tasks(rows, candidate, tasks):
    """Per task: what N1, N2 and S did and how it counts; None when a required row is missing."""
    out = {}
    for task in tasks:
        n1, n2, s = (rows.get((task, arm)) for arm in ("N1", "N2", candidate))
        if n1 is None or n2 is None or s is None:
            return None
        base = [bool(n1["passed"]), bool(n2["passed"])]
        took = bool(s["passed"])
        kind = ("new pass" if took and not any(base) else
                "regression" if not took and all(base) else
                "missed" if not took and sum(base) == 1 else
                "ceiling" if took and all(base) else "same")
        out[task] = {"N1": base[0], "N2": base[1], "S": took, "kind": kind}
    return out


def cell_result(per_task):
    counts = {kind: sum(1 for t in per_task.values() if t["kind"] == kind)
              for kind in ("new pass", "regression", "missed", "ceiling", "same")}
    if counts["new pass"] >= 2 and not counts["regression"] and not counts["missed"]:
        result = "improved"
    elif counts["regression"] >= 2:
        result = "worse"
    else:
        result = "undecided"
    return result, counts


def idle_pairs(rows_by_cell, candidate, idle_ids):
    """Per (cell, idle task): the pair's result with its reason; None when a required row is missing."""
    pairs = {}
    for cell in CELLS:
        for task in idle_ids:
            n, s = rows_by_cell[cell].get((task, "N")), rows_by_cell[cell].get((task, candidate))
            if n is None or s is None:
                return None
            pairs[(cell, task)] = {"n_tokens": n.get("startup_tokens"), "s_tokens": s.get("startup_tokens"),
                                   "n_solved": bool(n["passed"]), "s_solved": bool(s["passed"]),
                                   "used": s.get("used")}
    for (cell, task), pair in pairs.items():
        lost = pair["n_solved"] and not pair["s_solved"]
        other = pairs[(CELLS[1 - CELLS.index(cell)], task)]
        lost_there = other["n_solved"] and not other["s_solved"]
        tokens_known = bool(pair["n_tokens"]) and bool(pair["s_tokens"])
        pair["ratio"] = round(pair["s_tokens"] / pair["n_tokens"], 4) if tokens_known else None
        if tokens_known and pair["s_tokens"] > IDLE_RATIO * pair["n_tokens"]:
            pair["result"], pair["why"] = "fail", "startup tokens above 1.02 x N"
        elif lost and lost_there:
            pair["result"], pair["why"] = "fail", "N solved it and S did not, in both cells"
        elif lost:
            pair["result"], pair["why"] = "undecided", "N solved it and S did not, in this cell only"
        elif not pair["n_solved"] and not pair["s_solved"]:
            pair["result"], pair["why"] = "undecided", "neither N nor S solved it"
        elif not tokens_known:
            pair["result"], pair["why"] = "undecided", "startup tokens not recorded"
        else:
            pair["result"], pair["why"] = "pass", ""
    return pairs


def idle_result(pairs):
    results = [pair["result"] for pair in pairs.values()]
    return "fail" if "fail" in results else "undecided" if "undecided" in results else "pass"


def judge_candidate(rows_by_cell, incomplete, candidate, tasks, idle_ids):
    out = {"candidate": candidate, "cells": {}, "idle": None, "idle_pairs": None}
    reasons = [f"{cell}: {reason}" for cell in CELLS for reason in incomplete.get(cell, {}).get(candidate, [])]
    for cell in CELLS:
        per_task = cell_tasks(rows_by_cell[cell], candidate, tasks)
        if per_task is None:
            reasons.append(f"{cell}: a task run of N1, N2 or {candidate} is missing")
            continue
        result, counts = cell_result(per_task)
        out["cells"][cell] = {"result": result, "counts": counts, "tasks": per_task}
    pairs = idle_pairs(rows_by_cell, candidate, idle_ids)
    if pairs is None:
        reasons.append("an idle run of N or of the candidate is missing")
    else:
        out["idle"] = idle_result(pairs)
        out["idle_pairs"] = {f"{cell}/{task}": pair for (cell, task), pair in pairs.items()}
    if reasons:
        return dict(out, verdict="not completed", why=sorted(set(reasons)))
    results = [out["cells"][cell]["result"] for cell in CELLS]
    clean = all(not out["cells"][cell]["counts"]["regression"] and not out["cells"][cell]["counts"]["missed"]
                for cell in CELLS)
    if "worse" in results or out["idle"] == "fail":
        verdict = "not adopted"
        why = [f"{cell} is worse" for cell in CELLS if out["cells"][cell]["result"] == "worse"]
        why += ["the idle check fails"] if out["idle"] == "fail" else []
    elif "improved" in results and clean and out["idle"] == "pass":
        verdict, why = "optional", [f"{cell} improved" for cell in CELLS if out["cells"][cell]["result"] == "improved"]
    else:
        verdict, why = "below the bar", []
        if "improved" not in results:
            why.append("no cell improved")
        if not clean:
            why.append("a cell has a regression or a miss")
        if out["idle"] != "pass":
            why.append(f"the idle check is {out['idle']}")
    return dict(out, verdict=verdict, why=why)


def judge(rows_by_cell, incomplete, tasks, idle_ids, candidates=CANDIDATES):
    """rows_by_cell: {cell: [counted rows]}; incomplete: {cell: {candidate: [reasons]}}."""
    indexed = {cell: index(rows_by_cell.get(cell, [])) for cell in CELLS}
    out = {"tasks": list(tasks), "idle_tasks": list(idle_ids), "candidates": {}}
    for candidate in candidates:
        found = judge_candidate(indexed, incomplete, candidate, tasks, idle_ids)
        found["verdict_zh"] = VERDICTS[found["verdict"]]
        out["candidates"][candidate] = found
    out["ceiling"] = {candidate: {cell: sorted(
        task for task in tasks
        if all((task, arm) in indexed[cell] and indexed[cell][(task, arm)]["passed"] for arm in ("N1", "N2", candidate)))
        for cell in CELLS} for candidate in candidates}
    out["tokens"] = {cell: {} for cell in CELLS}
    for cell in CELLS:
        for (unit, arm), row in sorted(indexed[cell].items()):
            entry = out["tokens"][cell].setdefault(arm + ("-idle" if row.get("kind") == "idle" else ""),
                                                   {"runs": 0, "logical": 0, "noncache": 0})
            entry["runs"] += 1
            entry["logical"] += int(row.get("tokens_total") or 0)
            entry["noncache"] += int(row.get("tokens_noncache") or 0)
    return out


def load_state(state):
    rows = {cell: read_rows(os.path.join(state, f"rows-main-{cell}.jsonl")) for cell in CELLS}
    for cell in CELLS:
        for row in rows[cell]:
            evidence = (row.get("session") or {}).get("evidence") or {}
            skills = (row.get("session") or {}).get("skills") or []
            row["used"] = {"tool_calls_naming_a_candidate": evidence, "skills_loaded": sorted(set(skills))}
    incomplete = {cell: {} for cell in CELLS}
    for cell in CELLS:
        for entry in read_rows(os.path.join(state, f"incomplete-main-{cell}.jsonl")):
            incomplete[cell].setdefault(entry["candidate"], []).append(entry["reason"])
    tasks = [u["id"] for u in json.load(open(os.path.join(state, "units_ppt.json"), encoding="utf-8"))["units"]]
    idle = [u["id"] for u in json.load(open(os.path.join(state, "units_idle.json"), encoding="utf-8"))["units"]]
    return rows, incomplete, tasks, idle


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    result = judge(*load_state(sys.argv[1]))
    text = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True)
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
