#!/usr/bin/env bash
# Oracle: a local PDF whose file name is Chinese, passed as the percent-encoded file:// URL that
# Path.as_uri() produces (the journey's own recipe), must be added and sealed like an ASCII-named one.
# Exit 0 = correct, 1 = defect present. Works on a scratch copy of ./project.
set -u
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
PY=/usr/bin/python3
scratch="$(mktemp -d "$TMPDIR/oracle-b1.XXXXXX")"
trap 'rm -rf "$scratch"' EXIT
cp -a ./project "$scratch/project"
mkdir -p "$scratch/papers"
printf '%%PDF-1.4\n%% Offline sample paper (oracle)\n%%%%EOF\n' > "$scratch/papers/睡眠筆記.pdf"
url="$(cd "$scratch" && $PY -c 'from pathlib import Path; print(Path("papers/睡眠筆記.pdf").resolve().as_uri())')"
out="$($PY ./oaw/scripts/catalog.py add "$url" --target "$scratch/project" --json 2>&1)"
rc=$?
listing="$($PY ./oaw/scripts/catalog.py list --target "$scratch/project" --json 2>&1)"
OUT="$out" LISTING="$listing" RC="$rc" $PY - <<'PY'
import json, os, sys
rc = int(os.environ["RC"])
try:
    added = json.loads(os.environ["OUT"])
except ValueError:
    print("FAIL: catalog add did not print JSON:", os.environ["OUT"][:300]); sys.exit(1)
listing = os.environ["LISTING"]
problems = []
if rc != 0:
    problems.append(f"catalog add exited {rc}")
if added.get("failed"):
    problems.append("failed: " + json.dumps(added["failed"], ensure_ascii=False))
if len(added.get("tasted") or []) != 1:
    problems.append("the paper was not sealed (tasted is empty)")
if "睡眠筆記.pdf" not in listing:
    problems.append("catalog list does not show local/睡眠筆記.pdf")
if problems:
    print("FAIL (defect present): " + "; ".join(problems)); sys.exit(1)
print("PASS: the Chinese-named local PDF was added and sealed"); sys.exit(0)
PY
