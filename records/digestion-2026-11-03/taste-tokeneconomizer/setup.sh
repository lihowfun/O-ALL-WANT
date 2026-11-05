#!/usr/bin/env bash
# Tasting area for microsoft/TokenEconomizer (records/digestion-2026-11-03/taste-tokeneconomizer/PREREG.md).
# Builds the corpus copies, the pinned Claude Code CLI, the side-call shim and the food's official
# project-scope install. Nothing here is installed at user scope.
#
#   T=<tasting dir> RECORDS=<this folder> bash setup.sh
set -euo pipefail
: "${T:?tasting dir}" "${RECORDS:?this records folder}"
FOOD_SHA=519c65fff990e14480accca8a7629b3befcb7630
BASE=49943b5a94413a530761350f04e896f76e8d620e     # pallets/flask
CC_VERSION=2.1.310                                   # TokenEconomizer supports Claude Code 2.1.300-2.1.310
UV="${UV:-uv}"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
export DISABLE_AUTOUPDATER=1
mkdir -p "$T" && cd "$T"

[ -d food-src ] || git clone -q https://github.com/microsoft/TokenEconomizer.git food-src
git -C food-src checkout -q --detach "$FOOD_SHA"
[ -d cc ] || npm install --prefix ./cc --no-fund --no-audit "@anthropic-ai/claude-code@$CC_VERSION"
CLAUDE="$T/cc/node_modules/.bin/claude"
mkdir -p bin && cp "$RECORDS/sidecall_shim.py" bin/claude && chmod +x bin/claude
sed -i "s#^REAL = .*#REAL = \"$CLAUDE\"#" bin/claude

[ -d corpus-src ] || git clone -q https://github.com/pallets/flask.git corpus-src
for arm in verify N T; do
  [ -d "arm-$arm" ] || git clone -q corpus-src "arm-$arm"
  ( cd "arm-$arm" && git checkout -q --detach "$BASE" && git remote remove origin 2>/dev/null || true
    UV_PROJECT_ENVIRONMENT=.venv "$UV" sync -q --frozen --no-default-groups --group tests --python 3.12 )
done

# The food, official install, project scope (README "Claude Code" + plugin/README.md).
python3 -I "$RECORDS/snap_user_state.py" proof/before.json "$CLAUDE"
( cd arm-T
  "$CLAUDE" plugin marketplace add --scope project "$T/food-src"
  "$CLAUDE" plugin install --scope project tokeneconomizer@tokeneconomizer )
python3 -I "$RECORDS/snap_user_state.py" proof/after-install.json "$CLAUDE"

# Its state lives in the tasting area, not ~/.tokeneconomizer. Commands from a terminal are the
# documented free form of the slash commands (no model turn).
export TOKENECONOMIZER_HOME="$T/te-home" TASTE_SIDECALL_LOG="$T/te-sidecalls.jsonl"
export PATH="$T/bin:$(dirname "$CLAUDE"):/usr/bin:/bin"
TE="$T/food-src/plugin/scripts/te"
( cd arm-T
  "$TE" --host claude toolprune refresh-catalog
  "$TE" --host claude config set microskills=on
  "$TE" --host claude config set toolprune_quiet_minutes=0
  "$TE" --host claude config
  "$TE" --host claude doctor )

cat > arms.json <<EOF
{"N": {"dir": "$T/arm-N", "path_prepend": ["$T/bin"], "plugin_forbidden": "tokeneconomizer",
       "env": {"TOKENECONOMIZER_HOME": "$T/te-home-unused", "TASTE_SIDECALL_LOG": "$T/n-sidecalls.jsonl"},
       "sidecall_log": "$T/n-sidecalls.jsonl"},
 "T": {"dir": "$T/arm-T", "path_prepend": ["$T/bin"], "plugin_required": "tokeneconomizer",
       "env": {"TOKENECONOMIZER_HOME": "$T/te-home", "TASTE_SIDECALL_LOG": "$T/te-sidecalls.jsonl"},
       "sidecall_log": "$T/te-sidecalls.jsonl", "wait_for": "TOKENECONOMIZER_HOME=$T/te-home"}}
EOF
echo "arms.json written; verify the tasks next (verify_tasks.py), then run.sh"
