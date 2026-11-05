#!/usr/bin/env bash
# Run a frozen agent-level tasting, grade it blind and summarize (portable version of the 2026-11-04 run).
#
#   bash run_arms.sh <questions.json> <arms.json> [order, default N,G,S] [token budget, default 10000000]
#
# Env: CLAUDE (path to the logged-in claude CLI); TASTE_OUT (default: a new ~/taste/out-<timestamp>);
#      TASTE_RESUME=1 to continue an interrupted run in an existing TASTE_OUT (rows count toward the budget,
#      already-graded answers are not graded again).
# Freeze questions.json in records (with its sha256) before running. Raw stream-json stays in $TASTE_OUT/raw
# and is never published; rows/grades/summary are safe to commit.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
K="$HERE/../../digestion-2026-11-03/taste-graphify/agent"
if [ $# -lt 2 ]; then echo "usage: bash run_arms.sh <questions.json> <arms.json> [order] [budget]"; exit 2; fi
Q="$(realpath "$1")"; A="$(realpath "$2")"; ORDER="${3:-N,G,S}"; BUDGET="${4:-10000000}"
OUT="$(realpath -m "${TASTE_OUT:-$HOME/taste/out-$(date +%Y%m%d-%H%M%S)}")"
CLAUDE="${CLAUDE:-$(command -v claude)}"
if [ -z "$CLAUDE" ]; then echo "claude CLI not found; set CLAUDE"; exit 2; fi
if [ -s "$OUT/rows.jsonl" ] && [ -z "${TASTE_RESUME:-}" ]; then
  echo "$OUT already holds rows from another run; use a new TASTE_OUT, or TASTE_RESUME=1 to continue it"; exit 2
fi
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
mkdir -p "$OUT"
echo "out: $OUT"
sha256sum "$Q"
python3 "$K/taste_run.py" --questions "$Q" --arms "$A" --order "$ORDER" --repeat 1 \
  --claude "$CLAUDE" --out "$OUT" --budget "$BUDGET"
rc=$?
echo "run exit $rc"
if [ "$rc" -ne 0 ]; then
  echo "runner stopped (3 = token budget reached, 4 = billing is not the subscription); not grading - report to the owner"
  exit "$rc"
fi
python3 - "$A" <<'EOF'
import json, subprocess, sys
for arm, spec in json.load(open(sys.argv[1])).items():
    changed = subprocess.run(["git", "-C", spec["dir"], "status", "--short"], capture_output=True, text=True).stdout
    print(arm, "changes:", [l for l in changed.splitlines() if "graphify-out" not in l][:5])
EOF
# The grader runs with a cleared environment and --setting-sources project in a temp folder, so neither API-key
# variables nor a user settings "env" block reach it; its tokens are digestion overhead (D13).
python3 "$K/taste_grade.py" --questions "$Q" --rows "$OUT/rows.jsonl" --claude "$CLAUDE" --out "$OUT/grades.jsonl"
echo "grade exit $?"
python3 "$K/taste_summary.py" "$OUT/rows.jsonl" "$OUT/grades.jsonl" "$OUT/summary.json"
