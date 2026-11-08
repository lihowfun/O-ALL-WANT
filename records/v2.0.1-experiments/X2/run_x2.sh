#!/bin/bash
# X2 runs (PREREG.md). Usage: run_x2.sh calibrate|main|grade  (environment below; subscription billing only).
#   CASES     frozen folder with spec.json and cases/ (records X2/frozen)
#   OAW_SRC   `git archive` of claude/oaw-2 f1c9573 (the E install)
#   OUT       local output folder (transcripts and workspaces stay local)
#   CLAUDE, CODEX  CLI paths
#   SPENT     X2 Claude logical tokens before this step; CAP 60000000 (D36); RESERVE 8000000 for Claude grading
# Each cell's main run is two processes over interleaved halves of order.json, with the full order passed so the
# arm rotation by case position is unchanged; rows are merged per cell afterwards.
set -euo pipefail
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL OPENAI_API_KEY
HERE=$(cd "$(dirname "$0")" && pwd)
CAP=${CAP:-60000000}; RESERVE=${RESERVE:-8000000}; SPENT=${SPENT:?set SPENT}
step=${1:?calibrate|main|grade}

case "$step" in
calibrate)
  python3 -c "import json;print(json.dumps(json.load(open('$CASES/spec.json'))['calibration']))" > "$OUT/cal-order.json"
  python3 "$HERE/x2_run.py" --cell claude --cases "$CASES" --order "$OUT/cal-order.json" --oaw-src "$OAW_SRC" \
    --claude "$CLAUDE" --out "$OUT/cal-claude" --arms N --reps 3 --budget $((CAP - RESERVE)) --spent "$SPENT" &
  A=$!
  python3 "$HERE/x2_run.py" --cell codex --cases "$CASES" --order "$OUT/cal-order.json" --oaw-src "$OAW_SRC" \
    --codex "$CODEX" --out "$OUT/cal-codex" --arms N --reps 3 &
  B=$!
  wait $A; ea=$?; wait $B; eb=$?; echo "calibrate claude $ea codex $eb"
  ;;
main)
  python3 - "$CASES/spec.json" "$OUT" <<'EOF'
import json, sys
order = json.load(open(sys.argv[1]))["order"]
for name, half in (("a", order[0::2]), ("b", order[1::2])):
    open(f"{sys.argv[2]}/only-{name}.txt", "w").write(",".join(f"{arm}:{c}" for c in half for arm in "NRE"))
EOF
  json=$(python3 -c "import json;print(json.dumps(json.load(open('$CASES/spec.json'))['order']))"); echo "$json" > "$OUT/order.json"
  half=$(( (CAP - RESERVE - SPENT) / 2 ))
  pids=()
  for part in a b; do
    python3 "$HERE/x2_run.py" --cell claude --cases "$CASES" --order "$OUT/order.json" --oaw-src "$OAW_SRC" \
      --claude "$CLAUDE" --out "$OUT/claude-$part" --only "$(cat "$OUT/only-$part.txt")" --budget "$half" --spent 0 \
      > "$OUT/claude-$part.log" 2>&1 & pids+=($!)
    python3 "$HERE/x2_run.py" --cell codex --cases "$CASES" --order "$OUT/order.json" --oaw-src "$OAW_SRC" \
      --codex "$CODEX" --out "$OUT/codex-$part" --only "$(cat "$OUT/only-$part.txt")" \
      > "$OUT/codex-$part.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p" || echo "process $p exited $?"; done
  ;;
*) echo "unknown step $step"; exit 2 ;;
esac
