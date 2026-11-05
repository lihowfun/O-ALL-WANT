#!/usr/bin/env bash
# Read-only readiness check on a new Linux machine for OAW work and tasting runs.
# No model call unless --probe is given (then one tiny call with the long-lived token in an isolated config dir).
CLAUDE="${CLAUDE:-$(command -v claude)}"
TOKEN_FILE="${OAW_TASTE_TOKEN:-$HOME/.config/oaw-taste/claude-oauth-token}"
ok() { printf '  %-34s %s\n' "$1" "$2"; }

echo "[tools]"
for t in git python3 node npm gh curl jq openssl unzip gcc make sqlite3; do p=$(command -v "$t" 2>/dev/null); ok "$t" "${p:-MISSING}"; done
python3 -c 'import sys, venv, ensurepip; print("  python3", sys.version.split()[0], "(venv + ensurepip ok)")' 2>/dev/null \
  || ok "python3 venv/ensurepip" "MISSING (install python3-venv)"
command -v node >/dev/null && ok "node version (claude-mem needs >=20)" "$(node -v)"

echo "[claude]"
if [ -n "$CLAUDE" ]; then
  ok "claude" "$("$CLAUDE" --version 2>&1 | head -1)"
  "$CLAUDE" auth status 2>&1 | grep -E '"loggedIn"|"authMethod"|"subscriptionType"|"loginExpiresAt"' | sed 's/^/  /'
else ok "claude" MISSING; fi
for v in ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL; do
  if [ -n "${!v:-}" ]; then ok "$v" "SET - unset it (subscription only)"; else ok "$v" "unset"; fi; done
if [ -s "$TOKEN_FILE" ]; then ok "long-lived token file" "present, mode $(stat -c %a "$TOKEN_FILE")"; else ok "long-lived token file" "MISSING (owner: claude setup-token)"; fi

echo "[github]"
if command -v gh >/dev/null; then gh auth status 2>&1 | grep -E "Logged in|Token scopes" | sed 's/^ */  /'; fi
ok "git user.name" "$(git config --global user.name)"
case "$(git config --global user.email)" in *users.noreply.github.com) ok "git user.email" "noreply ok";; *) ok "git user.email" "NOT the noreply address";; esac

echo "[network / TLS]"
for h in github.com registry.npmjs.org pypi.org files.pythonhosted.org api.anthropic.com bun.sh astral.sh claude-mem.ai; do
  code=$(timeout 15 curl -sS -o /dev/null -w "%{http_code}" "https://$h/" 2>/dev/null)
  if [ "${code:-000}" = "000" ]; then
    issuer=$(echo | timeout 10 openssl s_client -connect "$h:443" -servername "$h" 2>/dev/null | openssl x509 -noout -issuer 2>/dev/null)
    ok "$h" "FAIL ${issuer:-no TLS}"
  else ok "$h" "$code"; fi
done
echo "  (a FAIL whose issuer is your company's CA means TLS inspection: trust that root CA in the system store)"

if [ "${1:-}" = "--probe" ]; then
  echo "[probe: one tiny call, isolated config dir, long-lived subscription token]"
  if [ ! -s "$TOKEN_FILE" ] || [ -z "$CLAUDE" ]; then
    echo "  skipped: token file or claude CLI missing"
  else
    CFG="$HOME/.config/oaw-taste/probe-config"; mkdir -p "$CFG"
    # node's folder too, in case claude is an npm install whose node lives elsewhere
    NODE_DIR="$(dirname "$(command -v node 2>/dev/null || echo /usr/bin/node)")"
    OUT=$(env -i HOME="$HOME" LANG=C.UTF-8 PATH="$(dirname "$CLAUDE"):$NODE_DIR:/usr/bin:/bin" CLAUDE_CONFIG_DIR="$CFG" \
          CLAUDE_CODE_OAUTH_TOKEN="$(cat "$TOKEN_FILE")" timeout 120 "$CLAUDE" -p "Reply with the single word OK." \
          --tools "" --strict-mcp-config --output-format stream-json --verbose 2>&1)
    OUT="$OUT" python3 -c "import json, os, re
s = os.environ['OUT']; init = {}; res = None
for line in s.splitlines():
    try:
        e = json.loads(line)
    except ValueError:
        continue
    if e.get('type') == 'system' and e.get('subtype') == 'init': init = e
    elif e.get('type') == 'result': res = e
if res is None:
    print('  probe failed:', re.sub(r'sk-ant-[A-Za-z0-9_-]+', '[redacted]', s)[:300])
else:
    print('  apiKeySource', init.get('apiKeySource'), '| model', init.get('model'), '| is_error', res.get('is_error'),
          '| result', repr((res.get('result') or '')[:20]))"
  fi
fi
