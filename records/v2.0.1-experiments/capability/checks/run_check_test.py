#!/usr/bin/env python3
"""A synthetic state folder through run_check.py: a run that failed first and counted on its second attempt must
reconcile, and a tampered ledger must not. usage: run_check_test.py <empty work folder>"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def write_rows(path, rows):
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def build(folder, tamper=""):
    os.makedirs(folder)
    lists = {"skills": ["a", "b"], "commands": ["a", "b", "c"]}
    freeze = {"launch": {"sequence": [["N1", "answer"], ["N2", "answer"], ["N", "idle"]], "idle_ids": ["t01"],
                         "cells": {"claude": {"allow": ["api.example:443"], "model": "model-x"},
                                   "codex": {"allow": ["chat.example:443"], "model": "model-y"}}},
              "tasks": {"p-t1": "0"}, "lock": {"files": {"cap_run.py": "runner"},
                                              "templates": {name: {"mounts": [f"/home/dev/{name}"]}
                                                            for name in ("common", "P1", "P2", "P3")}},
              "probes": {"claude": {"N": {"listed_skills": ["a", "b"], "startup_lists": lists}}, "codex": {}}}
    unit = {"id": "p-t1", "prompt": "x"}
    idle = {"id": "t01", "sessions": ["y"]}
    json.dump({"units": [unit]}, open(os.path.join(folder, "units_ppt.json"), "w"))
    json.dump({"units": [idle]}, open(os.path.join(folder, "units_idle.json"), "w"))
    freeze["units_ppt_sha256"] = hashlib.sha256(open(os.path.join(folder, "units_ppt.json"), "rb").read()).hexdigest()
    freeze["idle"] = {"units_sha256": hashlib.sha256(open(os.path.join(folder, "units_idle.json"), "rb").read()).hexdigest()}
    if tamper == "unit file":
        json.dump({"units": [dict(unit, prompt="other")]}, open(os.path.join(folder, "units_ppt.json"), "w"))
        unit = dict(unit, prompt="other")
    path = os.path.join(folder, "FREEZE.json")
    json.dump(freeze, open(path, "w"))
    digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
    shas = {u["id"]: hashlib.sha256(json.dumps(u, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            for u in (unit, idle)}
    bound = {"freeze_sha256": digest, "runner_sha256": "runner"}

    def start(unit, arm, attempt, kind):
        return dict(bound, event="start", unit=unit, arm=arm, attempt=attempt, kind=kind, unit_sha256=shas[unit],
                    root=f"runs/main/claude/{unit}/{arm}/a{attempt}")

    def done(unit, arm, attempt, kind, stamp, tokens, not_run=""):
        session = {"api_key_source": "none", "model": "model-x", "root_models": ["model-x", "model-x-20261101"],
                   "listed_skills": ["a", "b"], "startup_lists": lists, "mounts": ["/home/dev/common"],
                   "path": "/usr/bin" + (":venv" if kind == "idle" else ""), "mcp_servers": 0,
                   "net": {"allowed": {"api.example:443": 3}, "refused": {"telemetry.example:443": 1}},
                   "listed_tools": ["Bash"]}
        row = dict(start(unit, arm, attempt, kind), group="N", started=stamp, tokens_total=tokens, session=session,
                   grade={})
        if not_run:
            row["not_run"] = not_run
        return row

    starts = [start("p-t1", "N1", 1, "answer"), start("p-t1", "N1", 2, "answer"), start("p-t1", "N2", 1, "answer"),
              start("t01", "N", 1, "idle")]
    attempts = [done("p-t1", "N1", 1, "answer", "2026-01-01T00:00", 0, "startup lists differ"),
                done("p-t1", "N1", 2, "answer", "2026-01-01T00:01", 100),
                done("p-t1", "N2", 1, "answer", "2026-01-01T00:02", 120),
                done("t01", "N", 1, "idle", "2026-01-01T00:03", 50)]
    counted = [a for a in attempts if not a.get("not_run")]
    ledger = []
    for a in attempts:
        key = a["root"] + "/raw/s1.jsonl"
        ledger += [{"event": "start", "key": key}, {"event": "end", "key": key, "tokens": a["tokens_total"]}]
    if tamper == "extra row":
        counted.append(dict(counted[0]))
    if tamper == "dropped attempt":
        attempts = attempts[1:]
    if tamper == "out of order":
        counted[0]["started"], counted[2]["started"] = counted[2]["started"], counted[0]["started"]
    if tamper == "ledger":
        ledger[-1]["tokens"] += 1
    if tamper == "changed row":
        counted[0] = dict(counted[0], passed=True)
    if tamper == "wrong unit":
        attempts[1]["unit_sha256"] = counted[0]["unit_sha256"] = "other"
    write_rows(os.path.join(folder, "starts-main-claude.jsonl"), starts)
    write_rows(os.path.join(folder, "attempts-main-claude.jsonl"), attempts)
    write_rows(os.path.join(folder, "rows-main-claude.jsonl"), counted)
    write_rows(os.path.join(folder, "ledger-claude.jsonl"), ledger)
    return path


def main():
    base = os.path.abspath(sys.argv[1])
    bad = []
    for tamper, want in (("", 0), ("extra row", 1), ("dropped attempt", 1), ("out of order", 1), ("ledger", 1),
                         ("changed row", 1), ("wrong unit", 1), ("unit file", 1)):
        folder = os.path.join(base, tamper.replace(" ", "-") or "clean")
        freeze = build(folder, tamper)
        result = subprocess.run([sys.executable, os.path.join(HERE, "run_check.py"), folder, freeze],
                                capture_output=True, text=True)
        try:
            found = json.loads(result.stdout)
        except ValueError:
            found = {"problems": ["no JSON: " + result.stderr[-200:]], "notes": []}
        ok = result.returncode == want and (want == 1 or any("did not count" in n for n in found["notes"]))
        print(f"{'ok ' if ok else 'BAD'} {tamper or 'clean (failed first, counted second)'}: exit {result.returncode}, "
              f"{found['problems'][:2]}")
        if not ok:
            bad.append(tamper or "clean")
    print("all hold" if not bad else "FAILED: " + ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
