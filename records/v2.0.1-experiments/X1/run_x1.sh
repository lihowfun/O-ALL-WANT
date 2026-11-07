#!/usr/bin/env bash
# X1 of OAW 2.0.1 (PREREG.md). Every step resumes where it stopped.
#   SCRATCH=<local scratch> ERP_REPO=<frappe/erpnext clone> OAW_SRC=<git archive of claude/oaw-2 12799d9> \
#   CLAUDE=<claude CLI> bash run_x1.sh answers|rows|grade|judge
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
Q="$HERE/questions.json"
XG="$HERE/../../digestion-2026-11-07/validation/xgrade.py"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
export DISABLE_AUTOUPDATER=1
echo "a75a977596b7e1666682fa81b4b6547ab0765cac32c6df5aa249f88ecef31b7e  $Q" | sha256sum -c - || exit 2
echo "6ad7a60f4f744775cc32c43f95e488a30c46aab22fd1adcb7051e44854659948  $OAW_SRC/scripts/eval_stats.py" | sha256sum -c - || exit 2
echo "d6eb40e0f9d9aa2d05821d5e4caf265908bd816b47569553a12dbdaeb809ffdf  $XG" | sha256sum -c - || exit 2
BUDGET=${X1_BUDGET:-7600000}   # 8M cap minus 0.4M kept for the Opus grader; X1_BUDGET only after a new cap (PREREG)
SPENT=22114537   # question writer 20,068,719 + pilots 2,045,818, logical tokens (PREREG)
answers() {  # Opus cell first, then Haiku while the global guard allows
  python3 "$HERE/x1_run.py" --questions "$Q" --label opus --model claude-opus-5-5 --scratch "$SCRATCH" \
    --erp-repo "$ERP_REPO" --oaw-src "$OAW_SRC" --claude "$CLAUDE" --out "$SCRATCH/out-opus" \
    --budget $BUDGET --spent $SPENT --ledger "$SCRATCH/out-haiku" --timeout 1500 || return $?
  python3 "$HERE/x1_run.py" --questions "$Q" --label haiku --model claude-haiku-5-5 --scratch "$SCRATCH" \
    --erp-repo "$ERP_REPO" --oaw-src "$OAW_SRC" --claude "$CLAUDE" --out "$SCRATCH/out-haiku" \
    --budget $BUDGET --spent $SPENT --ledger "$SCRATCH/out-opus" --timeout 1500
}
rows() {
  for c in opus haiku; do
    mkdir -p "$HERE/out-$c"
    python3 "$HERE/x1_rows.py" "$SCRATCH/out-$c/rows.jsonl" "$SCRATCH" "$c" "$HERE/out-$c/rows.jsonl"
  done
}
grade() {  # both families, blind (xgrade builds the prompt from x1_grade.py's PROMPT and MASK)
  for c in opus haiku; do
    python3 "$XG" --kind codemap --module "$HERE/x1_grade.py" --rows "$HERE/out-$c/rows.jsonl" --ref "$Q" \
      --out "$HERE/out-$c/grades-opus.jsonl" --backend claude --model claude-opus-5-5 --effort high || return $?
    python3 "$XG" --kind codemap --module "$HERE/x1_grade.py" --rows "$HERE/out-$c/rows.jsonl" --ref "$Q" \
      --out "$HERE/out-$c/grades-codex.jsonl" --backend codex --model gpt-6.1-sol --effort high || return $?
  done
}
judge() {
  python3 "$HERE/x1_judge.py" --eval-stats "$OAW_SRC/scripts/eval_stats.py" --floor "$HERE/floor_sd.json" \
    --cell opus="$HERE/out-opus" --cell haiku="$HERE/out-haiku" --out "$HERE/judge.json"
}
"$1"
