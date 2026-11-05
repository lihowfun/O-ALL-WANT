"""Agent-level tasting runner for court-skill (D25, D26): the same frozen cases, one fresh `claude -p` session
per (arm, case, repeat), each in a fresh copy of the arm's template folder. Subscription billing only.

Adapted from ../taste-graphify/erpnext/taste_run.py. Changes: the arms differ by the ask (N, P) or by the
installed skill (C), not by the repository; every run gets its own copy of the arm template so one trial's
files never reach the next; the tool set allows file writes and sub-agents (the food needs both) and is the
same in every arm; token use counts sub-agents too (the result event's per-model totals, cross-checked
against the stream). The raw stream-json stays local (native transcripts are not published).

    arms.json: {"N": {"template": "<dir>"}, "P": {"template": "<dir>"}, "C": {"template": "<dir with .claude/skills/court>"}}
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

# Frozen asks (PREREG.md). The case text is the user's own words; each arm appends or prefixes its ask.
ASKS = {
    "N": "{case}\n\nIs this a good idea?",
    "P": ("{case}\n\nDon't just agree with me. Stress-test this: make the strongest honest case against it and the "
          "strongest case for it, then give me your bottom line on whether I should go ahead as described, and what "
          "would change your mind."),
    "C": "/court {case}",
}
TOOLS = "Read,Write,Edit,Glob,Grep,Bash,Agent"
ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "Agent", "Bash(python3:*)", "Bash(mkdir:*)", "Bash(ls:*)",
           "Bash(cat:*)"]


def _usage_sum(usage):
    return sum(int(usage.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                                                 "cache_read_input_tokens"))


def run_one(arm, template, case, rep, claude, out, timeout, model, effort, setting_sources):
    work = os.path.join(out, "work", f"{arm}-{case['id']}-r{rep}")
    if os.path.exists(work):
        shutil.rmtree(work)
    shutil.copytree(template, work)
    env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "TERM": "dumb",
           "PATH": ":".join([os.path.dirname(claude), "/usr/bin", "/bin"])}
    argv = [claude, "-p", ASKS[arm].format(case=case["case"]), "--output-format", "stream-json", "--verbose",
            "--tools", TOOLS, "--allowedTools", *ALLOWED, "--permission-mode", "acceptEdits",
            "--strict-mcp-config", "--setting-sources", setting_sources, "--no-session-persistence"]
    if model:
        argv += ["--model", model]
    if effort:
        argv += ["--effort", effort]
    started = time.time()
    try:
        done = subprocess.run(argv, cwd=work, env=env, capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
        stdout, code = done.stdout, done.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        code = "timeout"
    seconds = round(time.time() - started, 1)
    with open(os.path.join(out, "raw", f"{arm}-{case['id']}-r{rep}.jsonl"), "w", encoding="utf-8") as handle:
        handle.write(stdout)
    row = {"arm": arm, "id": case["id"], "rep": rep, "exit": code, "seconds": seconds, "api_key_source": None,
           "answer": "", "tools": {}, "agent_calls": 0, "bash": [], "usage_main": {}, "model_usage": {},
           "subagent_models": [], "turns": None, "is_error": None, "skill_loaded": None}
    seen = {}
    sub_models = set()
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            row["api_key_source"] = event.get("apiKeySource")
            row["model"] = event.get("model")
            row["claude_code_version"] = event.get("claude_code_version")
            row["plugins"] = [p.get("name") for p in event.get("plugins") or []]
            row["skill_loaded"] = "court" in (event.get("skills") or []) or "court" in (event.get("slash_commands") or [])
        elif kind == "assistant":
            message = event.get("message", {})
            if event.get("parent_tool_use_id"):
                sub_models.add(message.get("model"))
            if message.get("id") and message.get("usage"):
                seen[message["id"]] = _usage_sum(message["usage"])
            if event.get("parent_tool_use_id"):
                continue  # count only the orchestrator's own tool calls below
            for block in message.get("content", []):
                if block.get("type") == "tool_use":
                    row["tools"][block["name"]] = row["tools"].get(block["name"], 0) + 1
                    if block["name"] in ("Agent", "Task"):
                        row["agent_calls"] += 1
                    if block["name"] == "Bash":
                        row["bash"].append(str(block.get("input", {}).get("command", ""))[:200])
        elif kind == "result":
            row["answer"] = event.get("result", "") or ""
            row["usage_main"] = event.get("usage", {}) or {}
            row["model_usage"] = event.get("modelUsage", {}) or {}
            row["turns"] = event.get("num_turns")
            row["is_error"] = event.get("is_error")
    model_total = sum(int(m.get(k) or 0) for m in row["model_usage"].values()
                      for k in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"))
    row["tokens_stream"] = sum(seen.values())
    row["tokens_model_usage"] = model_total
    row["tokens_total"] = max(model_total, row["tokens_stream"], _usage_sum(row["usage_main"]))
    row["subagent_models"] = sorted(m for m in sub_models if m)
    row["tool_calls"] = sum(row["tools"].values())
    row["answer_words"] = len(row["answer"].split())
    verdict = os.path.join(work, ".court")
    if os.path.isdir(verdict):
        tallies = [os.path.join(dp, "tally.json") for dp, _, fs in os.walk(verdict) if "tally.json" in fs]
        if tallies:
            tally = json.load(open(sorted(tallies)[-1], encoding="utf-8"))
            row["court_tally"] = {k: tally.get(k) for k in ("verdict", "guilty", "not_guilty", "no_vote")}
        row["court_verdict_md"] = any("VERDICT.md" in fs for _, _, fs in os.walk(verdict))
    return row


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", required=True)
    parser.add_argument("--arms", required=True)
    parser.add_argument("--order", default="N,P,C")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--ids", default="")
    parser.add_argument("--claude", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--budget", type=int, default=9_000_000)
    parser.add_argument("--timeout", type=int, default=2400)
    parser.add_argument("--model", default="")
    parser.add_argument("--effort", default="")
    parser.add_argument("--setting-sources", default="project")
    args = parser.parse_args(argv)
    cases = json.load(open(args.questions, encoding="utf-8"))["cases"]
    if args.ids:
        wanted = set(args.ids.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    arms = json.load(open(args.arms, encoding="utf-8"))
    order = args.order.split(",")
    os.makedirs(os.path.join(args.out, "raw"), exist_ok=True)
    rows_path = os.path.join(args.out, "rows.jsonl")
    spent, largest = 0, 0
    if os.path.exists(rows_path):
        for line in open(rows_path, encoding="utf-8"):
            tokens = json.loads(line).get("tokens_total", 0)
            spent += tokens
            largest = max(largest, tokens)
    for rep in range(1, args.repeat + 1):
        for case in cases:
            # Pair guard: a case starts only when every arm can still run on it, judged by the largest run so far.
            if spent >= args.budget or (largest and spent + len(order) * largest > args.budget):
                print(f"budget guard: {spent:,} spent, largest run {largest:,}; not starting {case['id']}", flush=True)
                return 3
            for arm in order:
                row = run_one(arm, arms[arm]["template"], case, rep, args.claude, args.out, args.timeout,
                              args.model, args.effort, args.setting_sources)
                with open(rows_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                if row["api_key_source"] not in (None, "none"):
                    print(f"billing source is {row['api_key_source']}, not the subscription; stopping", flush=True)
                    return 4
                if arm == "C" and row["skill_loaded"] is False:
                    print("court skill did not load in arm C; stopping", flush=True)
                    return 5
                spent += row["tokens_total"]
                largest = max(largest, row["tokens_total"])
                print(f"{arm} {case['id']} r{rep}: exit {row['exit']} {row['seconds']}s agents {row['agent_calls']} "
                      f"tools {row['tool_calls']} words {row['answer_words']} tokens {row['tokens_total']:,} "
                      f"(total {spent:,})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
