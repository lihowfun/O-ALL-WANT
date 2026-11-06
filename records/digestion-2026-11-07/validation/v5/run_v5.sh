#!/usr/bin/env bash
# V5 of PREREG.md. T=<EGM tasting dir> OAW=<claude/oaw-2 checkout> CLAUDE=<claude CLI> bash run_v5.sh
# 1. snapshot user plugin state; 2. reinstall EGM at project scope in the events-E workspace (the self-test had
# uninstalled it); 3. run; 4. uninstall and restore user plugin state; 5. grade with Opus (frozen grader) and Codex.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
FROZEN="$HERE/../../../digestion-2026-11-06/egm-selftest"
OUT="$HERE/out"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
export DISABLE_AUTOUPDATER=1
mkdir -p "$OUT" "$T/proof"
python3 -I "$FROZEN/snap_user_state.py" "$T/proof/v5_before_install.json" "$CLAUDE" > /dev/null
python3 -I - "$T" <<'PY'
import sys, tarfile, os, shutil
t = sys.argv[1]; ws = f"{t}/ws/events-E"
for e in os.listdir(ws):
    p = os.path.join(ws, e); shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)
tarfile.open(f"{t}/pristine/events-E.tar").extractall(ws, filter="data")
PY
( cd "$T/ws/events-E" && "$CLAUDE" plugin marketplace add --scope project "$T/egm-upstream" && "$CLAUDE" plugin install --scope project egm@egm )
ROOT="$(python3 -c "import json;print(json.load(open('$T/arms.json'))['E']['add_dir'])")"
test -f "$ROOT/skills/egm-review/SKILL.md" || { echo "plugin root missing: $ROOT"; exit 5; }
python3 -I "$FROZEN/snap_user_state.py" "$T/proof/v5_after_install.json" "$CLAUDE" > /dev/null
python3 "$HERE/v5_run.py" "$T/arms.json" "$CLAUDE" "$OUT"
rc=$?
echo "run exit $rc"
( cd "$T/ws/events-E" && "$CLAUDE" plugin uninstall --scope project egm@egm; "$CLAUDE" plugin marketplace remove egm ) || true
rm -rf "$HOME/.claude/plugins/cache/egm"
python3 -I "$FROZEN/snap_user_state.py" "$T/proof/v5_restored.json" "$CLAUDE" > /dev/null
python3 - "$T/proof/v5_before_install.json" "$T/proof/v5_restored.json" "$HERE/proof_v5.json" <<'PY'
import json, sys
a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
same = {k: a.get(k) == b.get(k) for k in sorted(set(a) | set(b))}
json.dump({"restored": same}, open(sys.argv[3], "w"), indent=1); print("restored", same)
PY
[ "$rc" -eq 0 ] || [ "$rc" -eq 3 ] || exit "$rc"
python3 "$FROZEN/taste_grade.py" --cases "$OAW/evals/egm-local" --rows "$OUT/rows.jsonl" --claude "$CLAUDE" \
  --out "$OUT/grades-opus.jsonl" --model claude-opus-5-5 --effort high || exit $?
python3 "$HERE/../xgrade.py" --kind egm --module "$FROZEN/taste_grade.py" --rows "$OUT/rows.jsonl" --ref "$OAW/evals/egm-local" \
  --out "$OUT/grades-codex-original.jsonl" --backend codex --model "${CODEX_MODEL:-gpt-6.1-sol}" --effort high || exit $?
echo "V5 done"
