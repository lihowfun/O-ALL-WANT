#!/usr/bin/env bash
# V4 of PREREG.md: regrade past answers with Codex, original order first for every dataset, then reversed.
# Stops at the first exit 6 (a grade did not run, e.g. the Codex usage limit); rerun to resume.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
R="$HERE/../.."
CG="$R/digestion-2026-11-06/taste-codegraph"
Q="$R/digestion-2026-11-03/taste-graphify/erpnext/questions.json"
EGM="$R/digestion-2026-11-06/egm-selftest"
CT="$R/digestion-2026-11-03/taste-court-skill"
OAW="${OAW:-/mnt/drugs/akuo/project/OAW/OAW-v2}"
M="${CODEX_MODEL:-gpt-6.1-sol}"
E="${CODEX_EFFORT:-high}"
for order in original reversed; do
  for cond in opus sonnet opus48 haiku; do
    mkdir -p "$HERE/v4/$cond"
    python3 "$HERE/xgrade.py" --kind codemap --module "$CG/taste_grade.py" --rows "$CG/out-$cond/rows.jsonl" --ref "$Q" \
      --out "$HERE/v4/$cond/grades-codex-$order.jsonl" --backend codex --model "$M" --effort "$E" --order "$order" || exit $?
  done
  mkdir -p "$HERE/v4/egm" "$HERE/v4/court"
  python3 "$HERE/xgrade.py" --kind egm --module "$EGM/taste_grade.py" --rows "$EGM/out/rows.jsonl" --ref "$OAW/evals/egm-local" \
    --out "$HERE/v4/egm/grades-codex-$order.jsonl" --backend codex --model "$M" --effort "$E" --order "$order" || exit $?
  cat "$CT/out/rows.jsonl" "$CT/out-c5/rows.jsonl" > "$HERE/v4/court/rows.jsonl"
  python3 "$HERE/xgrade.py" --kind court --module "$CT/taste_grade.py" --rows "$HERE/v4/court/rows.jsonl" \
    --ref "$CT/questions.json,$CT/questions-c5.json" \
    --out "$HERE/v4/court/grades-codex-$order.jsonl" --backend codex --model "$M" --effort "$E" --order "$order" || exit $?
done
echo "V4 done"
