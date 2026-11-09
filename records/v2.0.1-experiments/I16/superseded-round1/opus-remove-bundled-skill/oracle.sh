#!/usr/bin/env bash
# Oracle: removing a built-in skill whose SKILL.md the user edited must not report success.
# Documented: an edited SKILL.md blocks the package's removal. Correct: a nonzero exit and no "removed"
# status. Defect: exit 0 with status "removed" while the edited skill is still installed.
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
scratch="$(mktemp -d "$TMPDIR/oracle-b6.XXXXXX")"
trap 'rm -rf "$scratch"' EXIT
cp -a ./project "$scratch/project"
P="$scratch/project"
skill="$P/.agents/skills/oaw-codemap/SKILL.md"
[ -f "$skill" ] || { echo "setup problem: $skill is missing"; exit 2; }
printf '\nLocal team note: prefer the JSON form.\n' >> "$skill"
out="$($PY ./oaw/scripts/oaw.py remove oaw-codemap --target "$P" --apply --json 2>&1)"
rc=$?
status="$(OUT="$out" $PY -c 'import json,os; print(json.loads(os.environ["OUT"]).get("status",""))' 2>/dev/null)"
if [ "$rc" = 0 ] || [ "$status" = removed ]; then
  if [ -f "$skill" ]; then
    echo "FAIL (defect present): remove exited $rc with status '$status' but the edited oaw-codemap skill is still installed"
    exit 1
  fi
fi
echo "PASS: remove refused the edited skill (exit $rc, status '$status')"; exit 0
