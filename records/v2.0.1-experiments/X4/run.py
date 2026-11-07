import json, os, subprocess, sys, statistics
S = sys.argv[1]
env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")}
env["PATH"] = "<claude-cli-dir>:" + env["PATH"]
orders = [("bare", "v200", "v201"), ("v200", "v201", "bare"), ("v201", "bare", "v200")]
rows = []
for rep, order in enumerate(orders, 1):
    for config in order:
        cwd = f"{S}/p-{config}"
        out = subprocess.run(["claude", "-p", "Reply with OK.", "--output-format", "stream-json", "--verbose",
                              "--no-session-persistence"], cwd=cwd, env=env, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL).stdout
        prompt, key, n_skills = None, None, None
        for line in out.splitlines():
            try: e = json.loads(line)
            except ValueError: continue
            if e.get("type") == "system" and e.get("subtype") == "init":
                key = e.get("apiKeySource"); n_skills = len(e.get("skills") or [])
            if e.get("type") == "assistant" and prompt is None:
                u = e["message"].get("usage", {})
                prompt = sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        rows.append({"host": "claude", "config": config, "rep": rep, "prompt_tokens": prompt, "apiKeySource": key, "skills_listed": n_skills})
        cx = subprocess.run(["codex", "exec", "--json", "--skip-git-repo-check", "--sandbox", "read-only", "Reply with OK."],
                            cwd=cwd, env=env, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL).stdout
        first = None
        for line in cx.splitlines():
            try: e = json.loads(line)
            except ValueError: continue
            if e.get("type") == "turn.completed" and first is None:
                first = (e.get("usage") or {}).get("input_tokens")
        rows.append({"host": "codex", "config": config, "rep": rep, "prompt_tokens": first})
        print(rows[-2], rows[-1], flush=True)
json.dump(rows, open(f"{S}/rows.json", "w"), indent=1)
for host in ("claude", "codex"):
    med = {c: statistics.median([r["prompt_tokens"] for r in rows if r["host"] == host and r["config"] == c and r["prompt_tokens"] is not None] or [0]) for c in ("bare", "v200", "v201")}
    print(host, med, "v201-v200", med["v201"] - med["v200"])
