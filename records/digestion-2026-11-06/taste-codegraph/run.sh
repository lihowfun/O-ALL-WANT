#!/usr/bin/env bash
# codegraph tasting on ERPNext, 2026-11-06: only the codegraph arm C is new. N (native), G (graphify) and
# S (OAW code_index) are seeded from the 2026-11-05 confirmation (d389fe9), then all four arms are graded blind
# in one fresh batch and C is judged against N with the rules frozen in PREREG.md.
#
#   COND=opus|sonnet T=<tasting dir holding arms-codegraph.json and out-confirm-$COND> CLAUDE=<logged-in claude CLI> bash run.sh
#
# Env: TASTE_OUT (default $T/out-codegraph-$COND). An interrupted run continues where it stopped (rows are keyed).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
Q="$HERE/../../digestion-2026-11-03/taste-graphify/erpnext/questions.json"
A="$T/arms-codegraph.json"
OUT="$(realpath -m "${TASTE_OUT:-$T/out-codegraph-$COND}")"
case "$COND" in
  opus)   MODEL=claude-opus-5-5;   TURNS=0;  BUDGET=2000000 ;;
  sonnet) MODEL=claude-sonnet-5-5; TURNS=14; BUDGET=1400000 ;;
  *) echo "COND must be opus or sonnet"; exit 2 ;;
esac
GRADER=claude-opus-5-5
EFFORT=high
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
mkdir -p "$OUT"
echo "cond: $COND out: $OUT"
echo "b7604bca63a134d43962924f88d9c209b01060f7020b054b2b3b366790b2ad83  $Q" | sha256sum -c - || exit 2
if [ ! -s "$OUT/rows.jsonl" ]; then
  # Seed N, G and S from the confirmation run (same CLI, model, effort, prompt, copies); mark them seeded.
  python3 - "$T/out-confirm-$COND/rows.jsonl" "$OUT/rows.jsonl" <<'PY'
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8")]
with open(sys.argv[2], "w", encoding="utf-8") as out:
    for row in rows:
        if row["arm"] in ("N", "G", "S"):
            row["seeded"] = True
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
print("seeded", len(rows), "rows")
PY
fi
python3 "$HERE/taste_run.py" --questions "$Q" --arms "$A" --order C --repeat 3 --claude "$CLAUDE" \
  --out "$OUT" --budget "$BUDGET" --model "$MODEL" --effort "$EFFORT" --max-turns "$TURNS"
rc=$?
echo "run exit $rc"
if [ "$rc" -eq 3 ]; then
  echo "budget guard stopped before a new question; grading the completed questions only (PREREG)"
elif [ "$rc" -ne 0 ]; then
  echo "runner stopped (4 = billing is not the subscription, 5 = a run failed); not grading"
  exit "$rc"
fi
python3 "$HERE/taste_grade.py" --questions "$Q" --rows "$OUT/rows.jsonl" --claude "$CLAUDE" --out "$OUT/grades.jsonl" \
  --model "$GRADER" --effort "$EFFORT"
echo "grade exit $?"
python3 "$HERE/summary.py" "$OUT/rows.jsonl" "$OUT/grades.jsonl" "$OUT/summary.json"
