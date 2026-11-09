#!/usr/bin/env bash
# Oracle: annotating a topic that does not exist must fail with exit status 1 and write nothing.
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR" || exit 2

[ -f project/scripts/context_hub.py ] && [ -f project/docs/knowledge/Topic.md ] || { echo "setup missing"; exit 2; }
grep -q 'Team note about report caching.' project/docs/knowledge/Topic.md || { echo "unexpected Topic.md"; exit 2; }

work="$(mktemp -d "$TMPDIR/oracle-b6.XXXXXX")" || exit 2
trap 'rm -rf "$work"' EXIT
cp -a project "$work/project" || exit 2
page="$work/project/docs/knowledge/Topic.md"

# Sanity: the ordinary annotate succeeds.
(cd "$work/project" && /usr/bin/python3 scripts/context_hub.py annotate Topic 'Cache reports after each release.') \
  > "$work/ok.txt" 2>&1 || { echo "ordinary annotate failed"; cat "$work/ok.txt"; exit 2; }
grep -q 'Cache reports after each release.' "$page" || { echo "ordinary annotate did not write"; exit 2; }
sum_before="$(cksum < "$page")"

# A misspelled topic.
(cd "$work/project" && /usr/bin/python3 scripts/context_hub.py annotate Topik 'Second observation.') > "$work/out.txt" 2>&1
rc=$?
cat "$work/out.txt"
echo "exit status: $rc"
grep -q "Topic 'Topik' not found" "$work/out.txt" || { echo "no not-found message"; exit 2; }
[ ! -e "$work/project/docs/knowledge/Topik.md" ] || { echo "a page was created"; exit 2; }
[ "$(cksum < "$page")" = "$sum_before" ] || { echo "Topic.md changed"; exit 2; }
case "$rc" in
  1) exit 0 ;;
  0) exit 1 ;;   # the failure is reported as success
  *) exit 2 ;;
esac
