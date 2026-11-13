#!/usr/bin/env python3
"""Prepare and guard FIXCHECK; execute the byte-identical H1 runner via its custom tag."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
H1 = HERE.parent / "H1"
CANDIDATE = "c2d9852bf8cabf13fd86a4340ab89f69044cae5a"
FREEZE_SHA = "4943bf2ce02c9c9383828d201f59198f951c0446e263a5b05ba381095fa3a4d8"
SOURCE_ROWS = {
    "claude": "ef79735f9fc9ca988d5f8d68cbc398abe81fcafa17fd98ab7e511a46479fedb5",
    "codex": "7a4b68b594b1058677f91648c9fd45f95da8e7fd40bad94220a19ff368f555c8",
}
BOUND_FILES = ("FIXCHECK.md", "fixcheck.py", "thresholds.py", "test_fixcheck.py")
MANIFEST = HERE / "MANIFEST.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def git(*args, cwd=None):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def load_runner():
    if sha(H1 / "FREEZE.json") != FREEZE_SHA:
        raise ValueError("original H1 FREEZE changed")
    freeze = read(H1 / "FREEZE.json")
    for name, digest in freeze["files"].items():
        if sha(H1 / name) != digest:
            raise ValueError(f"original H1 {name} changed")
    spec = importlib.util.spec_from_file_location("frozen_h1", H1 / "h1_run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not all((module.STATE, module.BASE, module.OAW, module.HIDE, module.SHOW, module.BIN)):
        raise ValueError("configure H1_STATE/BASE/OAW/HIDE/RO/BIN")
    state = Path(module.STATE).resolve()
    if not any(state.is_relative_to(Path(p).resolve()) for p in module.HIDE + ["/home", "/tmp"]):
        raise ValueError("FIXCHECK state must be hidden from the model sandbox")
    return module, freeze


def candidate(runner):
    if git("rev-parse", "HEAD", cwd=runner.OAW) != CANDIDATE:
        raise ValueError("candidate HEAD differs")
    if git("status", "--porcelain", cwd=runner.OAW):
        raise ValueError("candidate worktree must be clean")


def copy(source, target):
    # Independent files/inodes, never hardlinks to the original experiment.
    subprocess.run(["cp", "-a", "--reflink=auto", str(source), str(target)], check=True)


def prepare(runner, freeze, old):
    candidate(runner)
    state = Path(runner.STATE).resolve()
    old = old.resolve()
    if state == old or state.is_relative_to(old) or old.is_relative_to(state):
        raise ValueError("new state must be separate from H1")
    if state.exists():
        raise ValueError("state already exists; use check/run to resume, never rebuild")
    # Check immutable references before creating anything.
    for klass, digest in freeze["units"].items():
        if sha(old / f"units_{klass}.json") != digest:
            raise ValueError("source unit digest differs")
    for cell, digest in SOURCE_ROWS.items():
        if sha(old / f"rows-main-{cell}.jsonl") != digest:
            raise ValueError("original counted rows changed")
    state.mkdir(parents=True)
    (state / "reference").mkdir()
    (state / "arms").mkdir()
    copy(old / "tools", state / "tools")
    for arm in ("N", "L"):
        copy(old / "arms" / arm, state / "arms" / arm)
    copy(old / "arms" / "suite_baseline.json", state / "arms" / "suite_baseline.json")
    for klass in "ABC":
        copy(old / f"units_{klass}.json", state / f"units_{klass}.json")
    for cell in SOURCE_ROWS:
        copy(old / f"rows-main-{cell}.jsonl", state / "reference" / f"rows-main-{cell}.jsonl")
    for arm in ("N", "L"):
        if runner.arm_facts(arm) != freeze["arms"][arm]:
            raise ValueError(f"source {arm} template differs")
    if runner.tools_facts() != freeze["tools"]:
        raise ValueError("H1 tools snapshot differs")
    if sha(runner.baseline_path()) != freeze["suite_baseline_sha256"]:
        raise ValueError("suite baseline differs")
    target = Path(runner.arm_dir("O"))
    target.parent.mkdir()
    copy(Path(runner.arm_dir("N")), target)
    setup = state / "arms" / "_home"
    setup.mkdir()
    command = ("set -e\npython3 /home/dev/OAW/scripts/oaw.py init --target /home/dev/proj --host both\n"
               "git add -A\ngit commit -q -m 'Install FIXCHECK candidate OAW'\n")
    result = subprocess.run(
        runner.sandbox(str(target), str(setup), None, ["/bin/bash", "-c", command], net=False,
                       extra=[("--ro-bind", runner.OAW, "/home/dev/OAW")]),
        env=runner.environment(tools=False), capture_output=True, text=True)
    if result.returncode:
        raise ValueError("candidate installation failed: " + result.stderr[-500:])
    recorded = {"base_commit": runner.BASE_COMMIT, "oaw_commit": CANDIDATE,
                "oaw_scripts_templates_clean": True, "tools": runner.tools_facts(),
                "arms": {arm: runner.arm_facts(arm) for arm in "NOL"},
                "suite_baseline_sha256": sha(runner.baseline_path())}
    write(state / "arms" / "arms.json", recorded)
    write(state / "budget.json", {"cap": 17_000_000, "decision": "D45", "spent_before": 0})
    print("Prepared independent state; no model calls. Next: freeze.")


def validate_runtime(runner, freeze):
    candidate(runner)
    if Path(runner.raise_path()).exists():
        raise ValueError("FIXCHECK does not allow a budget raise without a new owner decision")
    now = runner.manifest()
    if now["budget"] != {"cap": 17_000_000, "decision": "D45", "spent_before": 0}:
        raise ValueError("wrong independent budget")
    allowed = {"arms", "oaw_commit", "oaw_mode_sha256", "budget"}
    for key in freeze:
        if key not in allowed and now[key] != freeze[key]:
            raise ValueError(f"H1 environment changed: {key}")
    for arm in "NL":
        if now["arms"][arm] != freeze["arms"][arm]:
            raise ValueError(f"H1 {arm} changed")
    if now["oaw_commit"] != CANDIDATE or now["arms"]["O"]["uncommitted"]:
        raise ValueError("candidate provenance differs")
    for cell, digest in SOURCE_ROWS.items():
        if sha(Path(runner.STATE) / "reference" / f"rows-main-{cell}.jsonl") != digest:
            raise ValueError("reference counted rows changed")
    return now


def has_started(state):
    return any(p.stat().st_size for pattern in ("starts-fixcheck-*", "attempts-fixcheck-*", "rows-fixcheck-*.jsonl")
               for p in state.glob(pattern))


def freeze_manifest(runner, freeze):
    state = Path(runner.STATE)
    if has_started(state):
        raise ValueError("FIXCHECK started; cannot rewrite manifest")
    now = validate_runtime(runner, freeze)
    units = []
    for klass in "ABC":
        for unit in read(state / f"units_{klass}.json")["units"]:
            units.append({"id": unit["id"], "klass": klass, "type": unit.get("type"),
                          "sessions": len(unit["sessions"]), "sha256": runner.unit_digest(unit),
                          "functions": unit["functions"], "items": unit["items"],
                          "learning_sessions": [1, 2] if unit.get("type") == "superseded" else [1] if klass == "B" else []})
    rows = []
    for cell in SOURCE_ROWS:
        for row in runner.read_rows(state / "reference" / f"rows-main-{cell}.jsonl"):
            if row["arm"] not in ("O", "N1", "N2"):
                continue
            if row["freeze_sha256"] != FREEZE_SHA or row["runner_sha256"] != freeze["files"]["h1_run.py"]:
                raise ValueError("baseline row source differs")
            # Whitelist numeric/mechanical outcomes only; raw paths and transcript tails stay local.
            item = {key: row[key] for key in ("cell", "unit", "arm", "klass", "type", "score", "tokens_total")}
            item["grade"] = {key: row["grade"][key] for key in
                             ("error", "functions", "items", "n", "passed", "recall", "suite_regression")}
            rows.append(item)
    write(HERE / "BASELINES.json", {"source_row_sha256": SOURCE_ROWS, "rows": rows})
    manifest = {
        "schema": 1, "experiment": "H1-FIXCHECK-2026-11-13", "candidate_commit": CANDIDATE,
        "h1_freeze_sha256": FREEZE_SHA, "reference_rows_sha256": SOURCE_ROWS,
        "baseline_sha256": sha(HERE / "BASELINES.json"), "runtime": now, "units": units,
        "files": {name: sha(HERE / name) for name in BOUND_FILES},
        "method": {"tag": "fixcheck", "arms": ["O"], "cells": ["codex", "claude"],
                   "class_order": ["A", "B", "C"], "memory_M1_min": 3, "memory_total": 4,
                   "small_token_ratio_max": [6, 5], "large_score_drop_max": [1, 10],
                   "full_reruns": 0, "new_effectiveness_verdict": False},
    }
    write(MANIFEST, manifest)
    digest = sha(MANIFEST)
    write(state / "BINDING.json", {"manifest_sha256": digest})
    audit = {"manifest_sha256": digest, "rows": []}
    for cell in ("codex", "claude"):
        for unit in units:
            audit["rows"].append({"cell": cell, "unit": unit["id"], "row_sha256": None,
                                 "extra_required_review": False, "extra_deep": False,
                                 **{m: {"status": "unverified", "evidence": []} for m in ("M1", "M2", "M3", "R1", "R2")}})
    write(HERE / "EVENTS.template.json", audit)
    # Working audit stays private until reviewed/redacted; do not overwrite an audited file.
    if (state / "EVENTS.json").exists() and any(
            r.get("row_sha256") is not None for r in read(state / "EVENTS.json")["rows"]):
        raise ValueError("an audited events file exists")
    write(state / "EVENTS.json", audit)
    print("Frozen FIXCHECK manifest " + digest + "; no model calls.")


def check(runner, freeze, pushed=False):
    manifest = read(MANIFEST)
    if validate_runtime(runner, freeze) != manifest["runtime"]:
        raise ValueError("runtime no longer matches FIXCHECK manifest")
    for name, digest in manifest["files"].items():
        if sha(HERE / name) != digest:
            raise ValueError(f"FIXCHECK source changed: {name}")
    if sha(HERE / "BASELINES.json") != manifest["baseline_sha256"]:
        raise ValueError("public baseline changed")
    if read(Path(runner.STATE) / "BINDING.json")["manifest_sha256"] != sha(MANIFEST):
        raise ValueError("state binding differs")
    if pushed:
        repo = git("rev-parse", "--show-toplevel", cwd=HERE)
        for name in (*BOUND_FILES, "MANIFEST.json", "BASELINES.json", "EVENTS.template.json"):
            path = (HERE / name).relative_to(repo).as_posix()
            remote = subprocess.check_output(["git", "show", f"origin/records:{path}"], cwd=repo)
            if remote != (HERE / name).read_bytes():
                raise ValueError(f"not pushed to origin/records: {name}")
    return manifest


def run(runner, freeze, cell, klass):
    state = Path(runner.STATE)
    # Held over the model calls, serializes both cells and concurrent resumes.
    with (state / "fixcheck.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = check(runner, freeze, pushed=True)
        if not (HERE / "REVIEW.json").exists():
            raise ValueError("missing reviewed launch authorization record")
        review = read(HERE / "REVIEW.json")
        if review.get("manifest_sha256") != sha(MANIFEST) or review.get("verdict") != "PASS":
            raise ValueError("review does not approve this manifest")
        prerequisites = [(cell, k) for k in "ABC" if k < klass]
        if cell == "claude":
            prerequisites += [("codex", k) for k in "ABC"]
        for prior_cell, prior_class in prerequisites:
            done = runner.read_rows(state / f"rows-fixcheck-{prior_cell}.jsonl")
            expected = {u["id"] for u in manifest["units"] if u["klass"] == prior_class}
            if {r["unit"] for r in done if r["klass"] == prior_class and r["arm"] == "O"} != expected:
                raise ValueError(f"complete {prior_cell}/{prior_class} first")
        # Human-readable preflight is an attestation, never inferred from stale PID files.
        attestation = read(state / "PREFLIGHT.json")
        if attestation.get("manifest_sha256") != sha(MANIFEST) or attestation.get("other_experiments_running") is not False:
            raise ValueError("D39 preflight missing or incompatible")
        import time
        if not 0 <= time.time() - attestation.get("checked_unix", 0) <= 300:
            raise ValueError("D39 process preflight must be refreshed within five minutes of launch")
        args = SimpleNamespace(tag="fixcheck", cell=cell, klass=klass, arms="O",
                               only=None, model=None, units=None)
        return runner.cmd_run(args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--h1-state", type=Path, required=True)
    sub.add_parser("freeze")
    sub.add_parser("check")
    start = sub.add_parser("run")
    start.add_argument("--cell", choices=("codex", "claude"), required=True)
    start.add_argument("--klass", choices=list("ABC"), required=True)
    args = parser.parse_args()
    try:
        runner, frozen = load_runner()
        if args.command == "prepare":
            prepare(runner, frozen, args.h1_state)
        elif args.command == "freeze":
            freeze_manifest(runner, frozen)
        elif args.command == "check":
            check(runner, frozen)
            print("FIXCHECK inputs match; no model calls.")
        else:
            return run(runner, frozen, args.cell, args.klass)
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"FIXCHECK refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
