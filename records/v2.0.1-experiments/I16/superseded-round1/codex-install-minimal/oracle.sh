#!/usr/bin/env bash
set -euo pipefail
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
/usr/bin/python3 - <<'PY'
from pathlib import Path
import json
import subprocess
import sys

def init():
    result = subprocess.run(["/usr/bin/python3", "oaw/scripts/oaw.py", "init", "--target", "./project", "--json"],
                            capture_output=True, text=True, encoding="utf-8", timeout=15)
    if result.returncode:
        print("FAIL: init exits nonzero")
        sys.exit(1)
    return json.loads(result.stdout)

init()
policy = Path("project/AGENTS.md")
original = policy.read_bytes()
marker = b"\nProject policy: retain the team's release checklist and private API compatibility notes.\n"
edited = original + marker
try:
    policy.write_bytes(edited)
    result = init()
    action = next(row["action"] for row in result["actions"] if row["path"] == "AGENTS.md")
    if policy.read_bytes() != edited:
        backups = Path("project/.oaw/backups")
        recovered = any(marker in path.read_bytes() for path in backups.rglob("*") if path.is_file())
        print("FAIL: repeat init lost the custom policy; action=" + action + ", backup_has_edit=" + str(recovered))
        sys.exit(1)
    if action != "preserve-edit":
        print("FAIL: repeat init did not recognize the local edit")
        sys.exit(1)
    print("PASS: repeat init preserves the exact custom policy bytes")
finally:
    policy.write_bytes(original)
PY
