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

settings = Path("project/.oaw/settings.json")
original = settings.read_bytes() if settings.exists() else None
def cli(*args):
    result = subprocess.run(["/usr/bin/python3", "scripts/oaw_mode.py", *args, "--json"],
                            cwd="project", capture_output=True, text=True, encoding="utf-8", timeout=15)
    if result.returncode:
        print("FAIL: review-setting or estimate command exits nonzero")
        sys.exit(1)
    return json.loads(result.stdout)

try:
    cap = 1000000
    saved = cli("egm", "on", "--max-tokens", str(cap))
    before = cli("egm", "estimate", "docs/plans/small.md")
    if saved["egm_max_tokens"] != cap or before["egm_max_tokens"] != cap or not before["ask_first"]:
        print("FAIL: initial saved cap is not used by the estimate")
        sys.exit(1)
    cli("egm", "off")
    cli("egm", "on")
    after = cli("egm", "estimate", "docs/plans/small.md")
    on_disk = json.loads(settings.read_text(encoding="utf-8"))["review"]
    if after["egm_max_tokens"] != cap or not after["ask_first"] or on_disk.get("egm_max_tokens") != cap:
        print("FAIL: toggling EGM discarded the saved token cap; estimate cap=" + str(after["egm_max_tokens"]) + ", ask_first=" + str(after["ask_first"]))
        sys.exit(1)
    print("PASS: the saved token cap and ask_first survive EGM switch commands")
finally:
    if original is None:
        settings.unlink(missing_ok=True)
    else:
        settings.write_bytes(original)
PY
