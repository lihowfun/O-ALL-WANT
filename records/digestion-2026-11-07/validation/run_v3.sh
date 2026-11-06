#!/usr/bin/env bash
# V3 of PREREG.md: grade the 24 calibration answers twice with the Opus grader and twice with Codex, then score.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
R="$HERE/../.."
MOD="$R/digestion-2026-11-06/taste-codegraph/taste_grade.py"
Q="$R/digestion-2026-11-03/taste-graphify/erpnext/questions.json"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
for pass in 1 2; do
  python3 "$HERE/xgrade.py" --kind codemap --module "$MOD" --rows "$HERE/v3/rows.jsonl" --ref "$Q" --out "$HERE/v3/grades-opus-$pass.jsonl" \
    --backend claude --model claude-opus-5-5 --effort high --salt "v3-opus-$pass" --workers 3 || exit $?
  python3 "$HERE/xgrade.py" --kind codemap --module "$MOD" --rows "$HERE/v3/rows.jsonl" --ref "$Q" --out "$HERE/v3/grades-codex-$pass.jsonl" \
    --backend codex --model "${CODEX_MODEL:-gpt-6.1-sol}" --effort "${CODEX_EFFORT:-high}" --salt "v3-codex-$pass" --workers 3 || exit $?
done
python3 "$HERE/v3_calibration.py" score "$HERE/v3" "$HERE"/v3/grades-opus-1.jsonl "$HERE"/v3/grades-opus-2.jsonl \
  "$HERE"/v3/grades-codex-1.jsonl "$HERE"/v3/grades-codex-2.jsonl
