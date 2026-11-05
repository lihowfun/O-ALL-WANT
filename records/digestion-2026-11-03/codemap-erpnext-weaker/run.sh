#!/usr/bin/env bash
# Code-map check with weaker models on ERPNext (N native, G graphify, S OAW code_index), 2026-11-05.
# Same frozen questions, arms, runner, grader and summary as ../codemap-erpnext-confirm (fc0bbc5); only the
# answering model changes. Both conditions use graphify's own benchmark cap of 14 turns, like the Sonnet one.
#
#   COND=opus48|haiku T=<tasting dir holding arms-confirm.json> CLAUDE=<logged-in claude CLI> bash run.sh
#
# Env: TASTE_OUT (default $T/out-weaker-$COND). An interrupted run continues where it stopped (rows are keyed).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
C="$HERE/../codemap-erpnext-confirm"
Q="$HERE/../taste-graphify/erpnext/questions.json"
A="$T/arms-confirm.json"
OUT="$(realpath -m "${TASTE_OUT:-$T/out-weaker-$COND}")"
case "$COND" in
  opus48) MODEL=claude-opus-4-8;  BUDGET=3000000 ;;
  haiku)  MODEL=claude-haiku-5-5; BUDGET=2400000 ;;
  *) echo "COND must be opus48 or haiku"; exit 2 ;;
esac
TURNS=14
GRADER=claude-opus-5-5
EFFORT=high
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
mkdir -p "$OUT"
echo "cond: $COND model: $MODEL out: $OUT"
sha256sum -c - <<SUMS || exit 2
b7604bca63a134d43962924f88d9c209b01060f7020b054b2b3b366790b2ad83  $Q
dcab377b56afbfde1a4a6316d37ddfa49f4cae69c5dd06d82cf0b179d13bb563  $C/taste_run.py
85e4e114ed1b3f4cfefa82e3397494995e58e5f4d74e8e3441d33fcc5ad6d3ec  $C/taste_grade.py
94b689c8d676c0031b980a324390f083bcc385d43ba378da49471f13438b55bd  $C/confirm_summary.py
SUMS
python3 "$C/taste_run.py" --questions "$Q" --arms "$A" --order N,G,S --rotate --repeat 3 --claude "$CLAUDE" \
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
python3 "$C/taste_grade.py" --questions "$Q" --rows "$OUT/rows.jsonl" --claude "$CLAUDE" --out "$OUT/grades.jsonl" \
  --model "$GRADER" --effort "$EFFORT"
echo "grade exit $?"
python3 "$C/confirm_summary.py" "$OUT/rows.jsonl" "$OUT/grades.jsonl" "$OUT/summary.json"
