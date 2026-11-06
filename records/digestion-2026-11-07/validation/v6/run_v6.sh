#!/usr/bin/env bash
# V6 of PREREG.md. T=<court tasting dir> CLAUDE=<claude CLI> bash run_v6.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
FROZEN="$HERE/../../../digestion-2026-11-03/taste-court-skill"
OUT="$T/v6/out"
REC="$HERE/out"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
export DISABLE_AUTOUPDATER=1
# Arm D: court's SKILL.md frontmatter unchanged, body replaced by one neutral line, no other files.
D="$T/v6/arms/D/.claude/skills/court"
rm -rf "$T/v6/arms/D" && mkdir -p "$D"
python3 - "$T/arms/C/.claude/skills/court/SKILL.md" "$D/SKILL.md" <<'PY'
import sys
text = open(sys.argv[1], encoding="utf-8").read()
end = text.index("\n---", 3) + 4
open(sys.argv[2], "w", encoding="utf-8").write(text[:end] + "\n\n# court\n\nThis skill's procedure is not installed in this "
                                                "environment. Answer the user directly.\n")
PY
mkdir -p "$OUT" "$REC"
python3 "$HERE/v6_run.py" "$T" "$CLAUDE" "$FROZEN/questions.json" "$OUT"
rc=$?
echo "run exit $rc"
[ "$rc" -eq 0 ] || [ "$rc" -eq 3 ] || exit "$rc"
rm -rf "$OUT/work"
cp "$OUT/rows.jsonl" "$REC/rows.jsonl"
[ ! -f "$OUT/deviations.jsonl" ] || cp "$OUT/deviations.jsonl" "$REC/"
python3 "$FROZEN/taste_grade.py" --questions "$FROZEN/questions.json" --rows "$REC/rows.jsonl" --claude "$CLAUDE" \
  --out "$REC/grades-opus.jsonl" --model claude-opus-5-5 --effort high || exit $?
python3 "$HERE/../xgrade.py" --kind court --module "$FROZEN/taste_grade.py" --rows "$REC/rows.jsonl" --ref "$FROZEN/questions.json" \
  --out "$REC/grades-codex-original.jsonl" --backend codex --model "${CODEX_MODEL:-gpt-6.1-sol}" --effort high || exit $?
echo "V6 done"
