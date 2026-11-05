#!/usr/bin/env bash
# Code-map confirmation on ERPNext (N native, G graphify, S OAW code_index), 2026-11-05: run, grade blind, summarize.
#
#   COND=opus|sonnet T=<tasting dir holding arms-confirm.json> CLAUDE=<logged-in claude CLI> bash run.sh
#
# opus:   claude-opus-5-5, effort high, no turn cap, 3 repeats; rep 1 of N and G is seeded from the 2026-11-05
#         N-vs-G run (TASTE_OUT must hold those rows, marked "seeded").
# sonnet: claude-sonnet-5-5, effort high, at most 14 turns (graphify's own benchmark cap), 3 repeats.
# Env: TASTE_OUT (default $T/out-confirm-$COND). An interrupted run continues where it stopped (rows are keyed).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
Q="$HERE/../taste-graphify/erpnext/questions.json"
A="$T/arms-confirm.json"
OUT="$(realpath -m "${TASTE_OUT:-$T/out-confirm-$COND}")"
case "$COND" in
  opus)   MODEL=claude-opus-5-5;   TURNS=0;  BUDGET=3600000 ;;
  sonnet) MODEL=claude-sonnet-5-5; TURNS=14; BUDGET=2400000 ;;
  *) echo "COND must be opus or sonnet"; exit 2 ;;
esac
GRADER=claude-opus-5-5
EFFORT=high
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
mkdir -p "$OUT"
echo "cond: $COND out: $OUT"
echo "b7604bca63a134d43962924f88d9c209b01060f7020b054b2b3b366790b2ad83  $Q" | sha256sum -c - || exit 2
python3 "$HERE/taste_run.py" --questions "$Q" --arms "$A" --order N,G,S --rotate --repeat 3 --claude "$CLAUDE" \
  --out "$OUT" --budget "$BUDGET" --model "$MODEL" --effort "$EFFORT" --max-turns "$TURNS"
rc=$?
echo "run exit $rc"
if [ "$rc" -eq 3 ]; then
  echo "budget guard stopped before a new question; grading the completed questions only (PREREG)"
elif [ "$rc" -ne 0 ]; then
  echo "runner stopped (4 = billing is not the subscription, 5 = a run failed); not grading"
  exit "$rc"
fi
python3 - "$A" <<'PY'
import json, subprocess, sys
for arm, spec in json.load(open(sys.argv[1])).items():
    changed = subprocess.run(["git", "-C", spec["dir"], "status", "--short"], capture_output=True, text=True).stdout
    print(arm, "changes:", changed.split())
PY
python3 "$HERE/taste_grade.py" --questions "$Q" --rows "$OUT/rows.jsonl" --claude "$CLAUDE" --out "$OUT/grades.jsonl" \
  --model "$GRADER" --effort "$EFFORT"
echo "grade exit $?"
python3 "$HERE/confirm_summary.py" "$OUT/rows.jsonl" "$OUT/grades.jsonl" "$OUT/summary.json"
