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

progress = Path("project/.oaw/progress.json")
original = progress.read_bytes()
try:
    data = json.loads(original)
    item = next(item for item in data["items"] if item["id"] == "research")
    item.update(percent="40", basis="Read two design documents")
    progress.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    malformed_bytes = progress.read_bytes()
    for flags in (("--json",), ()):
        result = subprocess.run(
            ["/usr/bin/python3", "oaw/scripts/oaw_status.py", "--project", "./project", *flags],
            capture_output=True, text=True, encoding="utf-8", timeout=15)
        if result.returncode != 0:
            print("FAIL: a string percentage crashes the entire status command")
            sys.exit(1)
        if flags:
            summary = json.loads(result.stdout)["progress"]
            rows = {item["id"]: item for item in summary["items"]}
            if (summary["total"], summary["done"], summary["waiting"]) != (3, 1, 1) or rows["research"]["percent"] is not None:
                print("FAIL: status does not retain all tasks with the malformed percentage shown as unknown")
                sys.exit(1)
        elif "??????????   ?%  Read design options" not in result.stdout or "Review project notes" not in result.stdout:
            print("FAIL: text status does not display the valid tasks and unknown percentage")
            sys.exit(1)
        if progress.read_bytes() != malformed_bytes:
            print("FAIL: reading status altered the user's progress file")
            sys.exit(1)
    print("PASS: status retains all tasks and shows a string percentage as unknown in JSON and text")
finally:
    progress.write_bytes(original)
PY
