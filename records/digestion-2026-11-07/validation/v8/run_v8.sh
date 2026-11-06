#!/usr/bin/env bash
# V8 of PREREG.md and ADDENDUM-V8.md. CLAUDE=<claude CLI> bash run_v8.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
FROZEN="$HERE/../../../digestion-2026-11-06/taste-codegraph"
L=/home/akuo/taste-local
TC=/mnt/drugs/akuo/taste-codegraph
OUT="$TC/v8/out"
REC="$HERE/out"
Q="$HERE/questions.json"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
export DISABLE_AUTOUPDATER=1
echo "eee033ec39e248520fea77ed776607c8d168cacfd8cb9ad2ddd993904d5fe6d6  $Q" | sha256sum -c - || exit 2
test "$(git -C $L/vscode-N rev-parse HEAD)" = 29ad5e7ec8d963aa67226f58a4472697b21d6f35 || exit 2
test "$(git -C $L/vscode-C rev-parse HEAD)" = 29ad5e7ec8d963aa67226f58a4472697b21d6f35 || exit 2
test -d "$L/vscode-C/.codegraph" && test -f "$L/vscode-C/.claude/settings.json" || { echo "codegraph not installed in C"; exit 2; }
test ! -e "$L/vscode-N/.codegraph" && test ! -e "$L/vscode-N/.claude" || { echo "N is not native"; exit 2; }
mkdir -p "$OUT" "$REC"
# ADDENDUM-V8: VS Code ships its own .mcp.json (component-explorer); codegraph's install added its server to it. C gets
# only the codegraph entry; N runs with --strict-mcp-config and no --mcp-config, so it has no MCP server at all.
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); json.dump({'mcpServers': {'codegraph': d['mcpServers']['codegraph']}}, open(sys.argv[2], 'w'), indent=1)" \
  "$L/vscode-C/.mcp.json" "$TC/v8/mcp-codegraph.json"
cat > "$TC/v8/arms.json" <<JSON
{"N": {"dir": "$L/vscode-N", "tools": "Read,Grep,Glob", "allowed": "Read Grep Glob", "path_prepend": []},
 "C": {"dir": "$L/vscode-C", "tools": "Read,Grep,Glob,Bash", "allowed": "Read Grep Glob Bash(codegraph:*) mcp__codegraph__*",
       "path_prepend": ["$TC/npm/node_modules/.bin", "$TC/nodebin"], "env": {"CODEGRAPH_TELEMETRY": "0", "DO_NOT_TRACK": "1"},
       "mcp_config": "$TC/v8/mcp-codegraph.json"}}
JSON
python3 "$FROZEN/taste_run.py" --questions "$Q" --arms "$TC/v8/arms.json" --order N,C --rotate --repeat 3 --claude "$CLAUDE" \
  --out "$OUT" --budget 4591753 --timeout 1800 --model claude-opus-4-8 --effort high
rc=$?
echo "run exit $rc"
[ "$rc" -eq 0 ] || [ "$rc" -eq 3 ] || exit "$rc"
sed -e "s#$L#<taste>#g" -e "s#$TC#<taste>#g" -e "s#$HOME#<home>#g" "$OUT/rows.jsonl" > "$REC/rows.jsonl"
python3 "$FROZEN/taste_grade.py" --questions "$Q" --rows "$REC/rows.jsonl" --claude "$CLAUDE" --out "$REC/grades-opus.jsonl" \
  --model claude-opus-5-5 --effort high || exit $?
python3 "$HERE/../xgrade.py" --kind codemap --module "$FROZEN/taste_grade.py" --rows "$REC/rows.jsonl" --ref "$Q" \
  --out "$REC/grades-codex-original.jsonl" --backend codex --model "${CODEX_MODEL:-gpt-6.1-sol}" --effort high || exit $?
python3 "$HERE/v8_judge.py" "$REC/rows.jsonl" "$REC/grades-opus.jsonl" "$REC/grades-codex-original.jsonl" "$REC/judge.json"
echo "V8 done"
