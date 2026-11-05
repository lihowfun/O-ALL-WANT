#!/usr/bin/env bash
# Follow-up arm T2 alone (PREREG.md here). T=<tasting dir> bash run.sh   (arms-T2.json as in PREREG.md)
set -euo pipefail
: "${T:?tasting dir}"
HERE="$(cd "$(dirname "$0")" && pwd)"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
python3 -I "$HERE/../taste_run.py" --tasks "$HERE/../tasks.json" --arms "$T/arms-T2.json" \
  --ids t01,t02,t03,t04,t05,t07,t09,t10,t11,t12,t13,t14 --order T2 \
  --base 49943b5a94413a530761350f04e896f76e8d620e --claude "$T/cc/node_modules/.bin/claude" \
  --out "${OUT:-$T/out-T2}" --budget 4600000 --timeout 1500 --max-turns 60 \
  --model claude-opus-5-5 --effort high --setting-sources project,local
