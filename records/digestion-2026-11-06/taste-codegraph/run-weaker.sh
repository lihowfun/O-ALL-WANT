#!/usr/bin/env bash
# codegraph on the weaker-model conditions of 2026-11-05 (../../digestion-2026-11-03/codemap-erpnext-weaker, fd1895c),
# so codegraph is held to the same four conditions as graphify and the OAW code map (ADDENDUM-WEAKER.md).
# N, G and S are seeded from that run; only C is new; all arms are graded again in one fresh batch.
#
#   COND=opus48|haiku T=<tasting dir holding arms-codegraph.json and out-weaker-$COND> CLAUDE=<claude CLI> bash run-weaker.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
Q="$HERE/../../digestion-2026-11-03/taste-graphify/erpnext/questions.json"
A="$T/arms-codegraph.json"
OUT="$(realpath -m "${TASTE_OUT:-$T/out-codegraph-$COND}")"
case "$COND" in
  opus48) MODEL=claude-opus-4-8;  REPEAT=3; BUDGET=1200000 ;;
  haiku)  MODEL=claude-haiku-5-5; REPEAT=1; BUDGET=1000000 ;;
  *) echo "COND must be opus48 or haiku"; exit 2 ;;
esac
TURNS=14
GRADER=claude-opus-5-5
EFFORT=high
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
mkdir -p "$OUT"
echo "cond: $COND model: $MODEL out: $OUT"
echo "b7604bca63a134d43962924f88d9c209b01060f7020b054b2b3b366790b2ad83  $Q" | sha256sum -c - || exit 2
if [ ! -s "$OUT/rows.jsonl" ]; then
  python3 - "$T/out-weaker-$COND/rows.jsonl" "$OUT/rows.jsonl" <<'PY'
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
python3 "$HERE/taste_run.py" --questions "$Q" --arms "$A" --order C --repeat "$REPEAT" --claude "$CLAUDE" \
  --out "$OUT" --budget "$BUDGET" --model "$MODEL" --effort "$EFFORT" --max-turns "$TURNS"
rc=$?
echo "run exit $rc"
if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then echo "runner stopped; not grading"; exit "$rc"; fi
python3 "$HERE/taste_grade.py" --questions "$Q" --rows "$OUT/rows.jsonl" --claude "$CLAUDE" --out "$OUT/grades.jsonl" \
  --model "$GRADER" --effort "$EFFORT"
echo "grade exit $?"
python3 "$HERE/summary.py" "$OUT/rows.jsonl" "$OUT/grades.jsonl" "$OUT/summary.json"
