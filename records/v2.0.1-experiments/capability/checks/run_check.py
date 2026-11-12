#!/usr/bin/env python3
"""Reconcile the ledgers of a capability state folder and check what every counted run saw (PLAN.md section 12).

  ledgers    starts, attempts and rows agree in both directions; one counted row per (unit, arm); a start without an
             attempt is listed as interrupted; attempts are numbered without gaps; the claude ledger closes every
             session and adds up to the attempts
  binding    every main row carries the digests of the runner, its unit entry and FREEZE.json
  order      counted rows of a cell started in the frozen sequence
  isolation  billing source, model, the skills listed at startup (the frozen list of the group), the mounts of the
             group, one PATH per cell, no MCP server, the same built-in plugins and tools in every group, only
             allowlisted hosts reached
  files      every kept deliverable has the digest its row states

usage: run_check.py <state folder> <FREEZE.json>     exits 0 when nothing is wrong
"""
import hashlib
import json
import os
import re
import sys

CELLS = ("claude", "codex")
BILLING = {"claude": "none", "codex": "chatgpt"}


def rows(path):
    if not os.path.exists(path):
        return []
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def sha(path):
    total = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            total.update(block)
    return total.hexdigest()


def init_event(path):
    if not os.path.exists(path):
        return {}
    for line in open(path, encoding="utf-8", errors="replace"):
        if '"subtype":"init"' in line or '"subtype": "init"' in line:
            try:
                return json.loads(line)
            except ValueError:
                return {}
    return {}


def main():
    state, freeze_path = sys.argv[1], sys.argv[2]
    freeze = json.load(open(freeze_path, encoding="utf-8"))
    freeze_sha = sha(freeze_path)
    sequence = [tuple(item) for item in freeze["launch"]["sequence"]]
    tasks = list(freeze["tasks"])
    idle = freeze["launch"]["idle_ids"]
    allow = {cell: set(freeze["launch"]["cells"][cell]["allow"]) for cell in CELLS}
    templates = freeze["lock"]["templates"]
    mounts = {"N": templates["common"]["mounts"]}
    for group in ("P1", "P2", "P3"):
        mounts[group] = mounts["N"] + templates[group]["mounts"]
    problems, notes, summary = [], [], {}
    units = {}      # unit id -> digest of its frozen entry, as the runner computes it
    frozen_files = {"units_ppt.json": freeze.get("units_ppt_sha256"),
                    "units_idle.json": (freeze.get("idle") or {}).get("units_sha256")}
    for name in ("units_ppt.json", "units_idle.json"):
        path = os.path.join(state, name)
        if os.path.exists(path) and frozen_files[name] is not None and sha(path) != frozen_files[name]:
            problems.append(f"{name} is not the file that was frozen")
        if os.path.exists(path):
            for unit in json.load(open(path, encoding="utf-8"))["units"]:
                units[unit["id"]] = hashlib.sha256(json.dumps(unit, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    for tag in ("calibration", "main"):
        for cell in CELLS:
            starts = rows(os.path.join(state, f"starts-{tag}-{cell}.jsonl"))
            attempts = rows(os.path.join(state, f"attempts-{tag}-{cell}.jsonl"))
            counted = rows(os.path.join(state, f"rows-{tag}-{cell}.jsonl"))
            if not (starts or attempts or counted):
                continue
            where = f"{tag}/{cell}"
            start_roots, attempt_roots = [s["root"] for s in starts], [a["root"] for a in attempts]
            for name, values in (("start", start_roots), ("attempt", attempt_roots), ("row", [r["root"] for r in counted])):
                if len(values) != len(set(values)):
                    problems.append(f"{where}: a {name} is recorded twice")
            for a in attempts:
                if a["root"] not in start_roots:
                    problems.append(f"{where}: attempt {a['root']} has no start")
            for r in counted:
                match = [a for a in attempts if a["root"] == r["root"]]
                if len(match) != 1 or match[0].get("not_run"):
                    problems.append(f"{where}: row {r['root']} is not a counted attempt")
                elif match[0] != r:
                    problems.append(f"{where}: row {r['root']} differs from its attempt")
            for a in attempts:
                begun = [st for st in starts if st["root"] == a["root"]]
                if begun and any(begun[0].get(key) != a.get(key) for key in (
                        "unit", "arm", "attempt", "kind", "unit_sha256", "runner_sha256", "freeze_sha256")):
                    problems.append(f"{where}: attempt {a['root']} does not carry what its start recorded")
                if tag == "main" and units and a.get("unit_sha256") != units.get(a["unit"]):
                    problems.append(f"{where}: {a['root']} ran another version of {a['unit']} than the frozen one")
            for a in attempts:
                if not a.get("not_run") and a["root"] not in [r["root"] for r in counted]:
                    problems.append(f"{where}: counted attempt {a['root']} is missing from the rows")
            interrupted = [s["root"] for s in starts if s["root"] not in attempt_roots]
            if interrupted:
                notes.append(f"{where}: {len(interrupted)} started and never finished (counted as attempts): {interrupted}")
            keys = [(r["unit"], r["arm"]) for r in counted]
            if len(keys) != len(set(keys)):
                problems.append(f"{where}: two counted rows for one (unit, arm)")
            by_key = {}
            for s in starts:
                by_key.setdefault((s["unit"], s["arm"]), []).append(s["attempt"])
            for key, numbers in by_key.items():
                if sorted(numbers) != list(range(1, len(numbers) + 1)):
                    problems.append(f"{where}: attempts of {key} are numbered {sorted(numbers)}")
            failed = {}
            for a in attempts:
                if a.get("not_run"):
                    failed.setdefault(f"{a['unit']}/{a['arm']}", []).append(a["not_run"])
            if failed:
                notes.append(f"{where}: attempts that did not count: " + json.dumps(failed, ensure_ascii=False))
            if tag == "main":
                for r in starts + attempts + counted:
                    if r.get("freeze_sha256") != freeze_sha or r.get("runner_sha256") != freeze["lock"]["files"]["cap_run.py"]:
                        problems.append(f"{where}: {r['root']} is not bound to this FREEZE.json and its runner")
                        break
                order = [(r["arm"], r["kind"]) for r in sorted(counted, key=lambda r: r["started"])]
                collapsed = [order[i] for i in range(len(order)) if i == 0 or order[i] != order[i - 1]]
                if collapsed != [step for step in sequence if step in collapsed]:
                    problems.append(f"{where}: counted rows did not start in the frozen sequence: {collapsed}")
                expected = {(unit, arm) for arm, kind in sequence for unit in (tasks if kind == "answer" else idle)}
                missing = sorted(expected - set(keys))
                if missing:
                    notes.append(f"{where}: {len(missing)} runs of the sequence have no counted row: {missing}")
            paths, tools, plugins = {}, {}, {}
            for r in counted:
                session = r.get("session") or {}
                group = r["group"]
                if session.get("api_key_source") != BILLING[cell]:
                    problems.append(f"{where}: {r['root']} billing source {session.get('api_key_source')}")
                asked = freeze["launch"]["cells"][cell]["model"]
                roots = session.get("root_models") or []
                if (not roots or session.get("root_model_missing")
                        or not all(re.fullmatch(re.escape(asked) + r"(?:-\d{8})?", str(m)) for m in roots)):
                    problems.append(f"{where}: {r['root']} model {session.get('model')}")
                want = ((freeze["probes"].get(cell) or {}).get(group) or {}).get("listed_skills")
                if tag == "main" and sorted(session.get("listed_skills") or []) != (want or []):
                    problems.append(f"{where}: {r['root']} lists other skills than the frozen ones of {group}")
                lists = ((freeze["probes"].get(cell) or {}).get(group) or {}).get("startup_lists")
                if tag == "main" and cell == "claude" and session.get("startup_lists") != lists:
                    problems.append(f"{where}: {r['root']} startup lists differ from the frozen ones of {group}")
                if session.get("mounts") != mounts[group]:
                    problems.append(f"{where}: {r['root']} mounts {session.get('mounts')}")
                paths.setdefault(r["kind"], set()).add(session.get("path"))
                reached = set((session.get("net") or {}).get("allowed") or {})
                if not reached or reached - allow[cell]:
                    problems.append(f"{where}: {r['root']} reached {sorted(reached)}")
                tools.setdefault(json.dumps(session.get("listed_tools")), set()).add(group)
                if cell == "claude":
                    if session.get("mcp_servers"):
                        problems.append(f"{where}: {r['root']} has an MCP server")
                    event = init_event(os.path.join(state, r["root"], "raw", "s1.jsonl"))
                    plugins.setdefault(json.dumps(event.get("plugins"), sort_keys=True), set()).add(group)
                kept = os.path.join(state, r["root"], "grade", "deliverable", "output.pptx")
                stated = (r.get("grade") or {}).get("deliverable_sha256")
                if r["kind"] == "answer" and (os.path.exists(kept) or stated):
                    if not os.path.exists(kept) or sha(kept) != stated:
                        problems.append(f"{where}: {r['root']} deliverable does not match its digest")
            for kind, found in paths.items():
                if len(found) > 1:
                    problems.append(f"{where}: more than one PATH among the {kind} runs: {sorted(map(str, found))}")
            if len(tools) > 1:
                problems.append(f"{where}: the tools listed at startup differ between groups: "
                                + str([sorted(groups) for groups in tools.values()]))
            if len(plugins) > 1:
                problems.append(f"{where}: the plugins at startup differ between groups")
            if cell == "claude" and plugins:
                listed = json.loads(next(iter(plugins)))
                if any(p.get("path") != "builtin" for p in listed or []):
                    problems.append(f"{where}: a plugin that is not built in was loaded")
            refused = {}
            for r in counted:
                for host, times in ((r.get("session") or {}).get("net") or {}).get("refused", {}).items():
                    refused[host] = refused.get(host, 0) + times
            summary[where] = {"starts": len(starts), "attempts": len(attempts), "rows": len(counted),
                              "interrupted": len(interrupted), "refused_hosts": refused,
                              "tokens": sum(int(a.get("tokens_total") or 0) for a in attempts)}
    ledger = rows(os.path.join(state, "ledger-claude.jsonl"))
    started = {e["key"] for e in ledger if e["event"] == "start"}
    ended = {e["key"]: int(e.get("tokens") or 0) for e in ledger if e["event"] == "end"}
    if started - set(ended):
        notes.append(f"claude ledger: {len(started - set(ended))} sessions started and never ended (their reserve counts)")
    attempt_tokens = sum(int(a.get("tokens_total") or 0) for tag in ("calibration", "main")
                         for a in rows(os.path.join(state, f"attempts-{tag}-claude.jsonl")))
    run_keys = {k: v for k, v in ended.items() if "/probe/" not in k and not k.startswith("runs/probe")}
    known = {a["root"] for tag in ("calibration", "main")
             for a in rows(os.path.join(state, f"attempts-{tag}-claude.jsonl"))}
    for key in run_keys:    # a session that ended belongs to a recorded attempt
        if key.rsplit("/raw/", 1)[0] not in known:
            problems.append(f"claude ledger: the session {key} ended but its attempt is not recorded")
    if sum(run_keys.values()) != attempt_tokens:
        problems.append(f"claude ledger: sessions of runs add up to {sum(run_keys.values())}, attempts to {attempt_tokens}")
    summary["claude_ledger"] = {"sessions": len(started), "ended": len(ended), "tokens": sum(ended.values()),
                                "probe_tokens": sum(ended.values()) - sum(run_keys.values())}
    print(json.dumps({"problems": problems, "notes": notes, "summary": summary}, ensure_ascii=False, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
