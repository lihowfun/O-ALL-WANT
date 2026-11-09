#!/usr/bin/env bash
# Oracle: an add --apply that fails midway (a read-only skill folder for the second source) must roll
# back everything it wrote, so that after fixing the folder the same command succeeds and list shows both.
# Exit 0 = correct, 1 = defect present, 2 = cannot simulate (running as root ignores the read-only folder).
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
if [ "$(id -u)" = 0 ]; then echo "SKIP: a read-only folder cannot be simulated as root"; exit 2; fi
scratch="$(mktemp -d "$TMPDIR/oracle-b3.XXXXXX")"
trap 'chmod -R u+w "$scratch" 2>/dev/null; rm -rf "$scratch"' EXIT
cp -a ./project "$scratch/project"
cp -a ./local-skills "$scratch/local-skills"
P="$scratch/project"
mkdir -p "$P/.agents/skills/scripty"
chmod 555 "$P/.agents/skills/scripty"
$PY ./oaw/scripts/oaw.py add "$scratch/local-skills/notes" "$scratch/local-skills/scripty" --target "$P" --choice oaw --consent scripts --apply --json >"$scratch/first.json" 2>&1
first=$?
chmod 755 "$P/.agents/skills/scripty"
if [ "$first" = 0 ]; then echo "SKIP: the read-only folder did not make add fail"; exit 2; fi
if [ -e "$P/.agents/skills/notes" ]; then
  echo "FAIL (defect present): add failed (exit $first) and reported a rollback, but .agents/skills/notes was left behind"
  ls -R "$P/.agents/skills/notes"; exit 1
fi
rmdir "$P/.agents/skills/scripty"
$PY ./oaw/scripts/oaw.py add "$scratch/local-skills/notes" "$scratch/local-skills/scripty" --target "$P" --choice oaw --consent scripts --apply --json >"$scratch/second.json" 2>&1
second=$?
if [ "$second" != 0 ]; then echo "FAIL (defect present): retry after fixing the folder exited $second"; head -c 600 "$scratch/second.json"; exit 1; fi
listing="$($PY ./oaw/scripts/oaw.py list --target "$P" --json 2>&1)"
for name in notes scripty; do
  if ! LISTING="$listing" NAME="$name" $PY -c 'import json,os,sys; rows=json.loads(os.environ["LISTING"]); sys.exit(0 if os.environ["NAME"] in json.dumps(rows, ensure_ascii=False) else 1)'; then
    echo "FAIL (defect present): list does not show $name after the retry"; exit 1
  fi
done
echo "PASS: the failed add was rolled back and the retry installed both skills"; exit 0
