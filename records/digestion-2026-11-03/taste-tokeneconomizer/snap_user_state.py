"""Snapshot user-level Claude Code state (hashes only; never prints values)."""
import hashlib, json, os, subprocess, sys
H = os.path.expanduser("~")
def sha(p):
    try: return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except OSError: return None
def keyhash(obj): return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()
out = {"files": {p: sha(os.path.join(H, p)) for p in (
    ".claude/settings.json", ".claude/settings.local.json", ".claude.json",
    ".claude/plugins/installed_plugins.json", ".claude/plugins/known_marketplaces.json")}}
try:
    cj = json.load(open(os.path.join(H, ".claude.json")))
    out["claude_json_keys"] = sorted(cj)
    out["claude_json_plugin_keys"] = {k: keyhash(cj[k]) for k in cj if "plugin" in k.lower() or "marketplace" in k.lower()}
    out["claude_json_mentions_te"] = "tokeneconomizer" in json.dumps(cj).lower()
except Exception as e:
    out["claude_json_error"] = type(e).__name__
st = json.load(open(os.path.join(H, ".claude/settings.json")))
out["user_settings_enabledPlugins"] = sorted(st.get("enabledPlugins") or {})
out["user_settings_mentions_te"] = "tokeneconomizer" in json.dumps(st).lower()
for p in (".claude/plugins/installed_plugins.json", ".claude/plugins/known_marketplaces.json"):
    try: out[p + ":mentions_te"] = "tokeneconomizer" in open(os.path.join(H, p)).read().lower()
    except OSError: out[p + ":mentions_te"] = None
cli = sys.argv[2]
r = subprocess.run([cli, "plugin", "list", "--json"], capture_output=True, text=True, cwd=H,
                   env=dict(os.environ, DISABLE_AUTOUPDATER="1"))
try:
    lst = json.loads(r.stdout)
    out["plugin_list_from_home"] = sorted(f"{p.get('id') or p.get('name')}|{p.get('scope')}|{p.get('enabled')}" for p in lst)
except ValueError:
    out["plugin_list_from_home_raw_sha"] = hashlib.sha256(r.stdout.encode()).hexdigest()
json.dump(out, open(sys.argv[1], "w"), indent=1, sort_keys=True)
print(json.dumps({k: v for k, v in out.items() if k != "claude_json_keys"}, indent=1, sort_keys=True))
