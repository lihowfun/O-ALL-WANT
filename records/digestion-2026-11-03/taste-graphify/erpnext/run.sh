#!/usr/bin/env bash
# ERPNext agent-level tasting of graphify (N vs G), 2026-11-05: run, grade blind, summarize.
#
#   T=<tasting dir holding arms.json> CLAUDE=<logged-in claude CLI> bash run.sh
#
# Env: TASTE_OUT (default $T/out-<timestamp>); TASTE_RESUME=1 continues an interrupted run in TASTE_OUT.
# The raw stream-json stays in $TASTE_OUT/raw and is never published; rows/grades/summary are safe to commit.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
Q="$HERE/questions.json"
A="$T/arms.json"
OUT="$(realpath -m "${TASTE_OUT:-$T/out-$(date +%Y%m%d-%H%M%S)}")"
MODEL=claude-opus-5-5
EFFORT=high
BUDGET=6200000   # graphify's D13 cap (10M) minus the 3,790,470 tokens of the 2026-11-04 OAW run
if [ -s "$OUT/rows.jsonl" ] && [ -z "${TASTE_RESUME:-}" ]; then
  echo "$OUT already holds rows; use a new TASTE_OUT or TASTE_RESUME=1"; exit 2
fi
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
mkdir -p "$OUT"
echo "out: $OUT"
sha256sum "$Q"
python3 "$HERE/taste_run.py" --questions "$Q" --arms "$A" --order N,G --repeat 1 --claude "$CLAUDE" \
  --out "$OUT" --budget "$BUDGET" --model "$MODEL" --effort "$EFFORT"
rc=$?
echo "run exit $rc"
if [ "$rc" -eq 3 ]; then
  echo "budget guard stopped before a new question; grading the completed pairs only (PREREG)"
elif [ "$rc" -ne 0 ]; then
  echo "runner stopped (4 = billing is not the subscription); not grading"
  exit "$rc"
fi
python3 - "$A" <<'EOF'
import json, subprocess, sys
for arm, spec in json.load(open(sys.argv[1])).items():
    changed = subprocess.run(["git", "-C", spec["dir"], "status", "--short"], capture_output=True, text=True).stdout
    print(arm, "changes:", [l for l in changed.splitlines() if "graphify-out" not in l][:5])
EOF
python3 "$HERE/taste_grade.py" --questions "$Q" --rows "$OUT/rows.jsonl" --claude "$CLAUDE" --out "$OUT/grades.jsonl" \
  --model "$MODEL" --effort "$EFFORT"
echo "grade exit $?"
python3 "$HERE/../agent/taste_summary.py" "$OUT/rows.jsonl" "$OUT/grades.jsonl" "$OUT/summary.json"
