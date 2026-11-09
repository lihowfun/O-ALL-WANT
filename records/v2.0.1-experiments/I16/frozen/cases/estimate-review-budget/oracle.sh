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
    settings = Path("project/.oaw/settings.json")
    original = settings.read_bytes() if settings.exists() else None
    try:
        good(["scripts/oaw_mode.py", "egm", "on", "--max-tokens", "900000000", "--json"])
        args = ["scripts/oaw_mode.py", "egm", "estimate", "docs/plans/small.md", "docs/context.md", "--json"]
        baseline = good(args)
        need(baseline["bytes"] == 107300 and baseline["egm_max_tokens"] == 900000000
             and baseline["ask_first"] is False)
        settings.write_bytes(b'{"review": {"egm_max_tokens": 1000},')
        before = snapshot()
        p = call(args)
        need(snapshot() == before)
        if (p.returncode == 2 and p.stdout == "" and
            p.stderr.startswith("oaw_mode: .oaw/settings.json is not readable JSON (") and
            p.stderr.endswith("; fix or delete it\n")):
            print("PASS: malformed settings refused; project bytes unchanged")
            return 0
        if p.returncode == 0 and p.stderr == "":
            wrong = dict(baseline, egm_max_tokens=25000000,
                         ask_first=baseline["tokens_high"] > 25000000)
            if json.loads(p.stdout) == wrong:
                print("DEFECT: malformed settings silently replaced by the default budget")
                return 1
        return 2
    finally:
        if original is None:
            settings.unlink(missing_ok=True)
        else:
            settings.write_bytes(original)

try:
    sys.exit(check())
except Exception as exc:
    print("INCONCLUSIVE: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
    sys.exit(2)
PY
