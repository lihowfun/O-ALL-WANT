#!/usr/bin/env bash
# EGM self-test (PREREG.md): run N, E, P on the frozen egm-local cases, grade blind, summarize.
#
#   T=<tasting dir holding arms.json> OAW=<claude/oaw-2 checkout> CLAUDE=<logged-in claude CLI> bash run.sh
#
# Env: E_ESTIMATE (first estimate of one E run, from the probe). An interrupted run continues where it stopped.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$T/out"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
export DISABLE_AUTOUPDATER=1
mkdir -p "$OUT"
python3 "$HERE/taste_run.py" --arms "$T/arms.json" --claude "$CLAUDE" --out "$OUT" --repeat 3 \
  --cap 9000000 --estimate "E=${E_ESTIMATE:-0}" --model claude-opus-5-5 --effort high
rc=$?
echo "run exit $rc"
if [ "$rc" -eq 6 ]; then
  echo "stopped by the usage limit; nothing was recorded for the cut session; rerun after the reset to resume"
  exit 6
elif [ "$rc" -eq 3 ]; then
  echo "budget guard stopped before a new (case, repeat); grading the completed groups only (PREREG)"
elif [ "$rc" -ne 0 ]; then
  echo "runner stopped (4 = billing is not the subscription, 5 = plugin or run failure); not grading"
  exit "$rc"
fi
python3 "$HERE/taste_grade.py" --cases "$OAW/evals/egm-local" --rows "$OUT/rows.jsonl" --claude "$CLAUDE" \
  --out "$OUT/grades.jsonl" --model claude-opus-5-5 --effort high
grc=$?
echo "grade exit $grc"
if [ "$grc" -ne 0 ]; then
  echo "grading stopped (6 = a grader call did not run); rerun after the reset to resume"
  exit "$grc"
fi
python3 "$HERE/summary.py" "$OUT/rows.jsonl" "$OUT/grades.jsonl" "$OUT/summary.json"
