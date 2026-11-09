#!/usr/bin/env bash
# Oracle: a docstring holding 1,000 emoji must still be searchable by its English words.
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR" || exit 2

[ -f project/scripts/code_index.py ] && [ -f project/pkg/util.py ] || { echo "setup missing"; exit 2; }
grep -q 'Join path parts safely without escaping the root.' project/pkg/util.py || { echo "unexpected util.py"; exit 2; }

work="$(mktemp -d "$TMPDIR/oracle-b1.XXXXXX")" || exit 2
trap 'rm -rf "$work"' EXIT
cp -a project "$work/project" || exit 2

top() {  # print "<top path> <count of results that are pkg/util.py>" or nothing on failure
  (cd "$work/project" && /usr/bin/python3 scripts/code_index.py find 'join path parts safely' --no-cache --json) \
    > "$work/out.json" 2> "$work/err.txt" || return 3
  /usr/bin/python3 - "$work/out.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
results = data.get("results", [])
print(results[0]["path"] if results else "-", sum(1 for r in results if r.get("path") == "pkg/util.py"))
PY
}

before="$(top)" || { echo "find failed before the edit"; cat "$work/err.txt"; exit 2; }
[ "$before" = "pkg/util.py 1" ] || { echo "baseline find unexpected: $before"; exit 2; }

/usr/bin/python3 - "$work/project/pkg/util.py" <<'PY' || exit 2
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
old = '"""Join path parts safely without escaping the root."""'
new = '"""Join path parts safely without escaping the root. ' + "\U0001F600" * 1000 + '"""'
assert text.count(old) == 1
open(path, "w", encoding="utf-8").write(text.replace(old, new))
PY

after="$(top)"; rc=$?
if [ $rc -ne 0 ]; then echo "find failed after adding emoji (rc=$rc)"; cat "$work/err.txt"; exit 2; fi
echo "after emoji: $after"
case "$after" in
  "pkg/util.py 1") exit 0 ;;
  "pkg/util.py "*|"- "*) exit 2 ;;
  *) exit 1 ;;   # helper_func's docstring words no longer count: another file outranks it
esac
