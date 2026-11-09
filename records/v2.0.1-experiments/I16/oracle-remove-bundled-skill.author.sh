#!/usr/bin/env bash
# Oracle: after a remove --apply that fails midway and is rolled back, fixing the cause and
# running the same command again must succeed (no install lock left behind).
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR" || exit 2

[ "$(id -u)" != 0 ] || { echo "running as root: a read-only folder cannot make the write fail"; exit 2; }
skill=project/.agents/skills/oaw-codemap
[ -f project/.oaw/install.json ] && [ -f "$skill/SKILL.md" ] && [ -f "$skill/agents/openai.yaml" ] \
  || { echo "setup missing"; exit 2; }
[ ! -e project/.oaw/install.lock ] || { echo "lock present before the test"; exit 2; }

work="$(mktemp -d "$TMPDIR/oracle-b3.XXXXXX")" || exit 2
copy="$work/project"
trap 'chmod -R u+w "$work" 2>/dev/null; rm -rf "$work"' EXIT
cp -a project "$copy" || exit 2
oaw() { /usr/bin/python3 ./oaw/scripts/oaw.py "$@"; }

# 1. Interrupt: the skill folder is read-only, so retiring SKILL.md fails after other writes began.
chmod a-w "$copy/.agents/skills/oaw-codemap" || exit 2
oaw remove oaw-codemap --target "$copy" --apply --json > "$work/first.json" 2>&1; rc1=$?
chmod u+w "$copy/.agents/skills/oaw-codemap" || exit 2
echo "first run (read-only folder): exit $rc1"; cat "$work/first.json"
[ $rc1 -ne 0 ] && grep -q 'Write failed' "$work/first.json" || { echo "first run did not fail as expected"; exit 2; }
[ -f "$copy/.agents/skills/oaw-codemap/SKILL.md" ] && [ -f "$copy/.agents/skills/oaw-codemap/agents/openai.yaml" ] \
  || { echo "rollback did not restore the skill files"; exit 2; }
grep -q '"oaw-codemap"' "$copy/.oaw/install.json" || { echo "manifest changed by the failed run"; exit 2; }

# 2. Recovery: the cause is fixed; the same command again.
oaw remove oaw-codemap --target "$copy" --apply --json > "$work/second.json" 2>&1; rc2=$?
echo "second run: exit $rc2"; cat "$work/second.json"
if [ $rc2 -eq 0 ] && grep -q '"status": "removed"' "$work/second.json" \
   && [ ! -e "$copy/.agents/skills/oaw-codemap" ] && [ ! -e "$copy/.oaw/install.lock" ] \
   && ! grep -q '"oaw-codemap"' "$copy/.oaw/install.json"; then
  exit 0
fi
if [ $rc2 -ne 0 ] && grep -q 'stale lock exists' "$work/second.json" && [ -e "$copy/.oaw/install.lock" ] \
   && [ -f "$copy/.agents/skills/oaw-codemap/SKILL.md" ]; then
  exit 1
fi
exit 2
