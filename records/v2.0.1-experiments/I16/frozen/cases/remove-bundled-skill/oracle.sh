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

# Byte snapshot of everything the failed run must leave untouched (tightened after review 2).
snap() { (cd "$copy" && find .agents/skills/oaw-codemap .oaw/install.json -type f -print0 | sort -z | xargs -0 sha256sum); }
before="$(snap)" || exit 2
cp -a "$copy/.agents/skills/oaw-codemap" "$work/original-skill" || exit 2

# 1. Interrupt: the skill folder is read-only, so retiring SKILL.md fails after other writes began.
chmod a-w "$copy/.agents/skills/oaw-codemap" || exit 2
oaw remove oaw-codemap --target "$copy" --apply --json > "$work/first.json" 2>&1; rc1=$?
chmod u+w "$copy/.agents/skills/oaw-codemap" || exit 2
echo "first run (read-only folder): exit $rc1"; cat "$work/first.json"
[ $rc1 -eq 2 ] || { echo "first run exit $rc1, expected 2"; exit 2; }
/usr/bin/python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get("status")=="error" and "Write failed" in d.get("error","") else 1)' "$work/first.json" \
  || { echo "first run did not report the expected write failure"; exit 2; }
[ "$(snap)" = "$before" ] || { echo "the failed run did not restore the skill files and manifest byte for byte"; exit 2; }

# 2. Recovery: the cause is fixed; the same command again.
oaw remove oaw-codemap --target "$copy" --apply --json > "$work/second.json" 2>&1; rc2=$?
echo "second run: exit $rc2"; cat "$work/second.json"
if [ $rc2 -eq 0 ]; then
  # success must be confirmed positively: parsed output, parsed manifest, backup equal to the original bytes
  /usr/bin/python3 - "$work" "$copy" <<'PY'
import filecmp, json, os, sys
work, copy = sys.argv[1], sys.argv[2]
try:
    out = json.load(open(os.path.join(work, "second.json")))
    manifest = json.load(open(os.path.join(copy, ".oaw", "install.json")))
except (OSError, ValueError):
    sys.exit(2)
backup = os.path.join(copy, out.get("backup") or "/nonexistent", ".agents", "skills", "oaw-codemap")
original = os.path.join(work, "original-skill")
same = os.path.isdir(backup) and not filecmp.dircmp(original, backup).diff_files and all(
    filecmp.cmp(os.path.join(original, r, n), os.path.join(backup, r, n), shallow=False)
    for r, _d, names in ((os.path.relpath(b, original), d, f) for b, d, f in os.walk(original)) for n in names)
ok = (out.get("status") == "removed" and "oaw-codemap" not in (manifest.get("skills") or [])
      and isinstance(manifest.get("skills"), list) and not os.path.exists(os.path.join(copy, ".agents/skills/oaw-codemap"))
      and not os.path.exists(os.path.join(copy, ".oaw/install.lock")) and same)
sys.exit(0 if ok else 2)
PY
  exit $?
fi
if [ $rc2 -ne 0 ] && grep -q 'stale lock exists' "$work/second.json" && [ -e "$copy/.oaw/install.lock" ] \
   && [ -f "$copy/.agents/skills/oaw-codemap/SKILL.md" ]; then
  exit 1
fi
exit 2
