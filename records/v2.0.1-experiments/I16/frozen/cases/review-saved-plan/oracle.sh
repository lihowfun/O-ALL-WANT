#!/usr/bin/env bash
set -eu
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
exec /usr/bin/python3 - <<'PY'
import hashlib
import json
from pathlib import Path
import subprocess
import sys

def need(condition):
    if not condition:
        raise RuntimeError("Unexpected setup, command output, or resulting state")

def call(args, cwd="project"):
    return subprocess.run(["/usr/bin/python3", *args], cwd=cwd,
                          capture_output=True, text=True, timeout=8)

def good(args, cwd="project"):
    p = call(args, cwd)
    need(p.returncode == 0 and p.stderr == "")
    return json.loads(p.stdout)

def snapshot(root="project"):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in Path(root).rglob("*") if p.is_file()}

def check():
    plan = Path("project/docs/plans/cache.md")
    index = Path("project/.oaw/reviews/index.json")
    need(plan.is_file() and not index.exists())
    args = ["scripts/oaw_mode.py", "suggest", "--plan", "docs/plans/cache.md", "--json"]
    def design(data):
        need(data["mode"] == "deep")
        steps = [s for s in data["steps"] if s["step"] == "design-review"]
        need(len(steps) == 1)
        d = steps[0]
        need(d["how"] == "fresh-context" and d["targets"] == ["docs/plans/cache.md"]
             and len(d["reviews"]) == 1 and d["reviews"][0]["target"] == "docs/plans/cache.md")
        return d
    initial = design(good(args))
    need(initial["done"] is False and initial["reviews"][0]["done"] is False)
    original = plan.read_bytes()
    record = good(["scripts/oaw_mode.py", "reviewed", "docs/plans/cache.md", "--how", "fresh-context", "--json"])
    need(record["status"] == "done" and record["how"] == "fresh-context" and
         record["target"] == "docs/plans/cache.md" and
         record["sha256"] == hashlib.sha256(original).hexdigest())
    need(json.loads(index.read_text())["reviews"] == [record])
    reviewed = design(good(args))
    need(reviewed["done"] is True and reviewed["reviews"][0]["done"] is True)
    plan.write_bytes(original + b"\nUse a shared persistent cache with cross-process locking.\n")
    need(hashlib.sha256(plan.read_bytes()).hexdigest() != record["sha256"])
    before = snapshot()
    changed = design(good(args))
    p = call(args[:-1])
    need(p.returncode == 0 and p.stderr == "" and snapshot() == before)
    need(json.loads(index.read_text())["reviews"] == [record])
    marker = "[done for this file content]"
    if (changed["done"] is False and changed["reviews"][0]["done"] is False and
        marker not in p.stdout and "docs/plans/cache.md: reports in " in p.stdout):
        print("PASS: changed plan needs review; stored review and plan bytes unchanged")
        return 0
    if (changed["done"] is True and changed["reviews"][0]["done"] is True and
        marker in p.stdout and "docs/plans/cache.md: reviewed" in p.stdout):
        print("DEFECT: changed plan reported as reviewed using its old content record")
        return 1
    return 2

try:
    sys.exit(check())
except Exception as exc:
    print("INCONCLUSIVE: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
    sys.exit(2)
PY
