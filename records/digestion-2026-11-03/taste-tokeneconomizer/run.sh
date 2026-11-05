#!/usr/bin/env bash
# Runs the frozen stream (PREREG.md). T=<tasting dir> bash run.sh   (arms.json comes from setup.sh)
set -euo pipefail
: "${T:?tasting dir}"
HERE="$(cd "$(dirname "$0")" && pwd)"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
OUT="${OUT:-$T/out}"
python3 -I "$HERE/taste_run.py" --tasks "$HERE/tasks.json" --arms "$T/arms.json" \
  --ids t01,t02,t03,t04,t05,t07,t09,t10,t11,t12,t13,t14 --order N,T --alternate \
  --base 49943b5a94413a530761350f04e896f76e8d620e --claude "$T/cc/node_modules/.bin/claude" \
  --out "$OUT" --budget 10000000 --timeout 1500 --max-turns 60 \
  --model claude-opus-5-5 --effort high --setting-sources project,local
