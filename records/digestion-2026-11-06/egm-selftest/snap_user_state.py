"""Snapshot user-level Claude Code plugin state for the EGM self-test (hashes and EGM presence only; never values).

  python3 -I snap_user_state.py <out.json> <claude CLI>

Adapted from ../../digestion-2026-11-03/taste-tokeneconomizer/snap_user_state.py. Presence is checked by key
("egm@egm" plugin id, "egm" marketplace name), not by substring, because the tasting area's own path contains
"egm" and ~/.claude.json records every project path a session ran in. ~/.claude.json itself changes with every
session (project list, usage counters), so only its plugin-related keys are hashed. The owner's other plugins
are replaced by placeholders.
"""
import hashlib
import json
import os
import subprocess
import sys

H = os.path.expanduser("~")
PLUGIN, MARKET = "egm@egm", "egm"


def sha(path):
    try:
        return hashlib.sha256(open(os.path.join(H, path), "rb").read()).hexdigest()
    except OSError:
        return None


def load(path):
    try:
        return json.load(open(os.path.join(H, path), encoding="utf-8"))
    except (OSError, ValueError):
        return None


out = {"files": {p: sha(p) for p in (".claude/settings.json", ".claude/settings.local.json",
                                       ".claude/plugins/installed_plugins.json",
                                       ".claude/plugins/known_marketplaces.json")}}
installed = load(".claude/plugins/installed_plugins.json") or {}
out["installed_has_egm"] = PLUGIN in (installed.get("plugins") or installed)
markets = load(".claude/plugins/known_marketplaces.json") or {}
out["marketplaces_has_egm"] = MARKET in markets
settings = load(".claude/settings.json") or {}
out["user_enabledPlugins_has_egm"] = PLUGIN in (settings.get("enabledPlugins") or {})
out["user_enabledPlugins_count"] = len(settings.get("enabledPlugins") or {})
out["plugin_cache_egm_exists"] = os.path.isdir(os.path.join(H, ".claude/plugins/cache", MARKET))
out["marketplace_dir_egm_exists"] = os.path.isdir(os.path.join(H, ".claude/plugins/marketplaces", MARKET))
claude_json = load(".claude.json") or {}
out["claude_json_plugin_keys"] = {k: hashlib.sha256(json.dumps(claude_json[k], sort_keys=True).encode()).hexdigest()
                                  for k in sorted(claude_json) if "plugin" in k.lower() or "marketplace" in k.lower()}
result = subprocess.run([sys.argv[2], "plugin", "list", "--json"], capture_output=True, text=True, cwd=H,
                        env=dict(os.environ, DISABLE_AUTOUPDATER="1"))
try:
    listed, others = [], 0
    for item in json.loads(result.stdout):
        ident = item.get("id") or item.get("name") or ""
        if "egm" in ident.split("@"):
            listed.append(f"{ident}|{item.get('scope')}|{item.get('enabled')}")
        else:
            others += 1
            listed.append(f"other-plugin-{others}|{item.get('scope')}|{item.get('enabled')}")
    out["plugin_list_from_home"] = sorted(listed)
except ValueError:
    out["plugin_list_from_home_raw_sha"] = hashlib.sha256(result.stdout.encode()).hexdigest()
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1, sort_keys=True)
print(json.dumps(out, indent=1, sort_keys=True))
