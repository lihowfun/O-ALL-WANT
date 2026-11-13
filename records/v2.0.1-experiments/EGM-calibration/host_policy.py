"""CLI feature policy for every inference launch; no host invocation on import."""
CODEX_EXTERNAL_FEATURES = (
    'apps', 'plugins', 'remote_plugin', 'plugin_discovery_prefetch',
    'browser_use', 'browser_use_external', 'browser_use_full_cdp_access',
    'in_app_browser', 'computer_use', 'skill_mcp_dependency_install',
)

def codex_flags():
    return [arg for name in CODEX_EXTERNAL_FEATURES for arg in ('-c', 'features.'+name+'=false')] + [
        '-c', 'mcp_servers={}', '-c', 'web_search="disabled"']
