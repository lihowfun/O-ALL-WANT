#!/usr/bin/env bash
# ADDENDUM-HAIKU3.md: codegraph's Haiku arm to 3 repeats, then grading A (extend) and B (all 48 again).
#   T=<tasting dir> CLAUDE=<claude CLI> bash run-haiku3.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
Q="$HERE/../../digestion-2026-11-03/taste-graphify/erpnext/questions.json"
A="$T/arms-codegraph.json"; OUT="$T/out-codegraph-haiku"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
echo "b7604bca63a134d43962924f88d9c209b01060f7020b054b2b3b366790b2ad83  $Q" | sha256sum -c - || exit 2
python3 - "$T/out-weaker-haiku/rows.jsonl" "$OUT/rows.jsonl" <<'PY'
import json, sys
have = {(r["arm"], r["id"], r["rep"]) for r in (json.loads(l) for l in open(sys.argv[2], encoding="utf-8"))}
added = 0
with open(sys.argv[2], "a", encoding="utf-8") as out:
    for line in open(sys.argv[1], encoding="utf-8"):
        row = json.loads(line)
        if row["arm"] in ("N", "G", "S") and (row["arm"], row["id"], row["rep"]) not in have:
            row["seeded"] = True
            out.write(json.dumps(row, ensure_ascii=False) + "\n"); added += 1
print("seeded", added, "more rows")
PY
python3 "$HERE/taste_run.py" --questions "$Q" --arms "$A" --order C --repeat 3 --claude "$CLAUDE" --out "$OUT" \
  --budget 2200000 --model claude-haiku-5-5 --effort high --max-turns 14
rc=$?; echo "run exit $rc"
if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then echo "runner stopped; not grading"; exit "$rc"; fi
for G in grades.jsonl grades-b.jsonl; do
  python3 "$HERE/taste_grade.py" --questions "$Q" --rows "$OUT/rows.jsonl" --claude "$CLAUDE" --out "$OUT/$G" \
    --model claude-opus-5-5 --effort high
  echo "grade $G exit $?"
done
