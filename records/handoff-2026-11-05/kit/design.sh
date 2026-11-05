#!/usr/bin/env bash
# Fresh question designer (D26): a new claude -p session with native read-only tools in the base copy.
# It knows the food's claim, not OAW's implementation. Subscription billing only; its tokens are digestion overhead.
#
#   bash design.sh <design_prompt.txt> <base copy dir> <out dir>
#
# Env: CLAUDE (claude CLI path), CLAUDE_MODEL (optional; pin the same model the arms will use and record it in PREREG).
# The 2026-11-04 prompt (../../digestion-2026-11-03/taste-graphify/agent/design_prompt.txt) names OAW and scripts/;
# write a new prompt for another repo. The stream-json transcript stays local (never published). The designer's
# final answer is written to <out>/design_result.md; review it, save the questions as questions.json, freeze it in
# records with its sha256, and only then run the arms.
set -euo pipefail
if [ $# -lt 3 ]; then echo "usage: bash design.sh <prompt file> <base dir> <out dir>"; exit 2; fi
PROMPT="$(cat "$1")"
BASE="$(realpath "$2")"
OUT="$(realpath -m "$3")"
CLAUDE="${CLAUDE:-$(command -v claude)}"
MODEL_ARGS=()
if [ -n "${CLAUDE_MODEL:-}" ]; then MODEL_ARGS=(--model "$CLAUDE_MODEL"); fi
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
mkdir -p "$OUT"
cd "$BASE"
"$CLAUDE" -p "$PROMPT" "${MODEL_ARGS[@]}" --output-format stream-json --verbose \
  --tools "Read,Grep,Glob" --allowedTools "Read Grep Glob" \
  --strict-mcp-config > "$OUT/design_stream.jsonl" 2> "$OUT/design_err.txt" || echo "claude exit $?"
git status --short | head || true
python3 - "$OUT/design_stream.jsonl" "$OUT/design_result.md" <<'EOF'
import json, sys
init, result = {}, None
for line in open(sys.argv[1], encoding="utf-8"):
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if event.get("type") == "system" and event.get("subtype") == "init":
        init = event
    elif event.get("type") == "result":
        result = event
print("apiKeySource:", init.get("apiKeySource"), "| model:", init.get("model"))
if result is None:
    print("no result event; see design_err.txt")
    sys.exit(1)
usage = result.get("usage") or {}
print("tokens (overhead):", sum(int(usage.get(k) or 0) for k in ("input_tokens", "output_tokens",
      "cache_creation_input_tokens", "cache_read_input_tokens")))
open(sys.argv[2], "w", encoding="utf-8").write(result.get("result") or "")
print("wrote", sys.argv[2])
EOF
tail -c 400 "$OUT/design_err.txt" || true
