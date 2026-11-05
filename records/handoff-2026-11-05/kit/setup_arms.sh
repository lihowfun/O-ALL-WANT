#!/usr/bin/env bash
# Tasting copies for an agent-level code-understanding tasting (D25, D26), portable version of what ran on
# 2026-11-04: base (question designer), N (native), G (graphify as its authors intend), S (OAW code_index).
# Writes $TASTE_DIR/arms.json with absolute paths (taste_run.py does not expand "~").
#
#   OAW repo (default):   COMMIT=51b00db bash setup_arms.sh
#   Another repo (N vs G): SRC=https://github.com/<owner>/<repo>.git COMMIT=<sha> ARMS="base N G" bash setup_arms.sh
#
# Env: SRC (git URL or path; default the OAW repo), COMMIT, ARMS (default "base N G S"; S needs an OAW checkout),
#      TASTE_DIR (default ~/taste), GRAPHIFY_BIN (default ~/oaw-graphify-run/env/bin), G_IGNORE (lines for
#      .graphifyignore; default "example/" for OAW - set what the food's docs recommend for other repos).
# graphify env (once): python3 -m venv ~/oaw-graphify-run/env && ~/oaw-graphify-run/env/bin/pip install graphifyy==0.9.101
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
AGENT_KIT="$HERE/../../digestion-2026-11-03/taste-graphify/agent"
SRC="${SRC:-https://github.com/lihowfun/O-ALL-WANT.git}"
COMMIT="${COMMIT:-51b00db}"
ARMS="${ARMS:-base N G S}"
T="$(realpath -m "${TASTE_DIR:-$HOME/taste}")"
GENV="$(realpath -m "${GRAPHIFY_BIN:-$HOME/oaw-graphify-run/env/bin}")"
G_IGNORE="${G_IGNORE-example/}"
mkdir -p "$T"
for arm in $ARMS; do
  rm -rf "${T:?}/$arm"
  git clone -q --no-checkout "$SRC" "$T/$arm"
  git -C "$T/$arm" checkout -q --detach "$COMMIT"
  git -C "$T/$arm" remote remove origin
  git -C "$T/$arm" log --oneline -1
done

case " $ARMS " in *" G "*)
  # G: the food's recommended ignore file, the code graph (AST only, no LLM), project-scope install.
  if [ -n "$G_IGNORE" ]; then printf '%s\n' "$G_IGNORE" > "$T/G/.graphifyignore"; fi
  (cd "$T/G" && env -i HOME="$HOME" PATH="$GENV:/usr/bin:/bin" LANG=C.UTF-8 "$GENV/graphify" update . 2>&1 \
     | { grep -v 'AST extraction:' || true; } | tail -4)
  (cd "$T/G" && env -i HOME="$HOME" PATH="$GENV:/usr/bin:/bin" LANG=C.UTF-8 "$GENV/graphify" install --project \
     --platform claude 2>&1 | tail -12)
  git -C "$T/G" status --short ;;
esac

case " $ARMS " in *" S "*)
  # S: OAW's own index, announced the way graphify announces itself (an always-on CLAUDE.md block).
  cat "$AGENT_KIT/s_block.md" >> "$T/S/CLAUDE.md"
  git -C "$T/S" status --short ;;
esac

ARMS="$ARMS" T="$T" GENV="$GENV" python3 - <<'EOF'
import json, os
t, genv, arms = os.environ["T"], os.environ["GENV"], os.environ["ARMS"].split()
spec = {
    "N": {"dir": f"{t}/N", "tools": "Read,Grep,Glob", "allowed": "Read Grep Glob", "path_prepend": []},
    "G": {"dir": f"{t}/G", "tools": "Read,Grep,Glob,Bash", "allowed": "Read Grep Glob Bash(graphify:*)",
          "path_prepend": [genv]},
    "S": {"dir": f"{t}/S", "tools": "Read,Grep,Glob,Bash",
          "allowed": "Read Grep Glob Bash(python3 scripts/code_index.py:*)", "path_prepend": []},
}
out = {name: spec[name] for name in arms if name in spec}
json.dump(out, open(f"{t}/arms.json", "w"), indent=1)
print("wrote", f"{t}/arms.json", "arms:", ",".join(out))
EOF
echo "--- user-level Claude settings must not have changed:"; cat "$HOME/.claude/settings.json" 2>/dev/null || echo "(none)"
