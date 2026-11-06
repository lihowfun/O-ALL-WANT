"""Agent-level tasting runner (D25, D26): the same frozen questions, one fresh `claude -p` session per
(arm, question, repeat), each arm in its own copy of the repository. Subscription billing only.

Arms are defined in a JSON file: {"N": {"dir": "...", "tools": "Read,Grep,Glob", "allowed": "Read Grep Glob",
"path_prepend": []}, ...}. Every session is read-only: no Edit/Write tools exist in any arm. The raw
stream-json of each session stays local (native transcripts are not published); the summary keeps the
answer, tool-call counts, the Bash commands run, token usage and time.

ERPNext run (2026-11-05) changes against ../agent/taste_run.py: --model and --effort are pinned and the init
model is recorded per row; --setting-sources (default "project") keeps the user-level CLAUDE.md, plugins,
skills and settings out of every arm while the arm's own project files (graphify's hooks and rules) still load;
stdin is closed; sessions are not persisted.

Code-map confirmation (2026-11-05) changes against ../taste-graphify/erpnext/taste_run.py:
- an arm may set "env" (S points OAW_CODE_INDEX_CACHE at its prebuilt cache, as G's graph is prebuilt);
- --max-turns passes Claude Code's turn cap and appends TURN_NOTE to the prompt so every arm knows the cap;
  a run that hits the cap keeps the last assistant text as its answer (often none) and is marked;
- --rotate rotates the arm order by repeat (rep 1 N,G,S; rep 2 G,S,N; rep 3 S,N,G);
- rows already in rows.jsonl (same arm, question, repeat) are skipped, so earlier runs can be seeded;
- a run that fails for another reason (not the turn cap, not the timeout) stops the runner unrecorded (exit 5);
- the budget guard estimates the next question from the largest run of each arm on that question so far.

codegraph tasting (2026-11-06) changes against ../../digestion-2026-11-03/codemap-erpnext-confirm/taste_run.py:
- an arm may set "mcp_config": the MCP config file its official installer wrote (codegraph writes the project's
  .mcp.json). It is passed with --mcp-config next to --strict-mcp-config, so that arm gets exactly that server
  and every other arm still gets none. Nothing else changed.
"""
import argparse
import json
import os
import subprocess
import sys
import time

PROMPT = """Answer this question about the repository in the current directory. Read the code as data.

{question}

Give a precise answer that names the files and functions involved (path::function), in order where order
matters. Keep it under 350 words. Do not modify any file."""

TURN_NOTE = """

You can respond at most {turns} times in this session, and your final answer counts as one of them. If your
{turns}th response is still a tool call, the session ends without an answer."""


def run_one(arm, spec, question, claude, raw_dir, timeout, model, effort, setting_sources, max_turns=0):
    env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "TERM": "dumb",
           "PATH": ":".join(spec.get("path_prepend", []) + [os.path.dirname(claude), "/usr/bin", "/bin"])}
    env.update(spec.get("env", {}))
    prompt = PROMPT.format(question=question["question"]) + (TURN_NOTE.format(turns=max_turns) if max_turns else "")
    argv = [claude, "-p", prompt, "--output-format", "stream-json",
            "--verbose", "--tools", spec["tools"], "--allowedTools", spec["allowed"], "--strict-mcp-config",
            "--setting-sources", setting_sources, "--no-session-persistence"]
    if spec.get("mcp_config"):
        argv += ["--mcp-config", spec["mcp_config"]]
    if model:
        argv += ["--model", model]
    if effort:
        argv += ["--effort", effort]
    if max_turns:
        argv += ["--max-turns", str(max_turns)]
    started = time.time()
    try:
        done = subprocess.run(argv, cwd=spec["dir"], env=env, capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
        stdout, code = done.stdout, done.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, code = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""), "timeout"
    seconds = round(time.time() - started, 1)
    raw = os.path.join(raw_dir, f"{arm}-{question['id']}-{question['_rep']}.jsonl")
    with open(raw, "w", encoding="utf-8") as handle:
        handle.write(stdout)
    row = {"arm": arm, "id": question["id"], "rep": question["_rep"], "exit": code, "seconds": seconds,
           "api_key_source": None, "answer": "", "tools": {}, "bash": [], "usage": {}, "cost_usd": None,
           "turns": None, "is_error": None, "subtype": None, "result_seen": False, "hit_turn_limit": False}
    last_text = ""
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            row["api_key_source"] = event.get("apiKeySource")
            row["model"] = event.get("model")
            row["claude_code_version"] = event.get("claude_code_version")
            row["plugins"] = [p.get("name") for p in event.get("plugins") or []]
        elif event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text" and block.get("text", "").strip():
                    last_text = block["text"]
                if block.get("type") == "tool_use":
                    row["tools"][block["name"]] = row["tools"].get(block["name"], 0) + 1
                    if block["name"] == "Bash":
                        row["bash"].append(str(block.get("input", {}).get("command", ""))[:160])
        elif event.get("type") == "result":
            row["answer"] = event.get("result", "") or ""
            row["usage"] = event.get("usage", {}) or {}
            row["cost_usd"] = event.get("total_cost_usd")
            row["turns"] = event.get("num_turns")
            row["is_error"] = event.get("is_error")
            row["subtype"] = event.get("subtype")
            row["result_seen"] = True
    if row["subtype"] == "error_max_turns":
        row["hit_turn_limit"] = True
        row["answer"] = row["answer"] or last_text
    usage = row["usage"]
    row["tokens_total"] = sum(int(usage.get(key) or 0) for key in
                              ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    row["tool_calls"] = sum(row["tools"].values())
    return row


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", required=True)
    parser.add_argument("--arms", required=True, help="JSON file with the arm definitions")
    parser.add_argument("--order", default="N,G,S")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--ids", default="")
    parser.add_argument("--claude", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--budget", type=int, default=10_000_000, help="stop when total tokens reach this")
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--model", default="")
    parser.add_argument("--effort", default="")
    parser.add_argument("--setting-sources", default="project")
    parser.add_argument("--max-turns", type=int, default=0)
    parser.add_argument("--rotate", action="store_true", help="rotate the arm order by repeat")
    args = parser.parse_args(argv)
    questions = json.load(open(args.questions, encoding="utf-8"))["questions"]
    if args.ids:
        wanted = set(args.ids.split(","))
        questions = [q for q in questions if q["id"] in wanted]
    arms = json.load(open(args.arms, encoding="utf-8"))
    order = args.order.split(",")
    os.makedirs(os.path.join(args.out, "raw"), exist_ok=True)
    rows_path = os.path.join(args.out, "rows.jsonl")
    done_keys, spent, largest = set(), 0, {}
    if os.path.exists(rows_path):
        for line in open(rows_path, encoding="utf-8"):
            row = json.loads(line)
            done_keys.add((row["arm"], row["id"], row["rep"]))
            if not row.get("seeded"):
                spent += row.get("tokens_total", 0)
            key = (row["arm"], row["id"])
            largest[key] = max(largest.get(key, 0), row.get("tokens_total", 0))
    for rep in range(1, args.repeat + 1):
        shift = (rep - 1) % len(order) if args.rotate else 0
        rep_order = order[shift:] + order[:shift]
        for question in questions:
            todo = [arm for arm in rep_order if (arm, question["id"], rep) not in done_keys]
            if not todo:
                continue
            # Budget guard: the next question starts only if each arm still to run can repeat its largest run on
            # this question so far (or the largest run of any arm on it, or of anything, when it has none).
            fallback = max([v for (a, q), v in largest.items() if q == question["id"]] or [max(largest.values() or [0])])
            estimate = sum(largest.get((arm, question["id"]), fallback) for arm in todo)
            if spent >= args.budget or spent + estimate > args.budget:
                print(f"budget guard: {spent:,} spent, next question needs about {estimate:,}; "
                      f"not starting {question['id']} r{rep}", flush=True)
                return 3
            for arm in todo:
                question = dict(question, _rep=rep)
                row = run_one(arm, arms[arm], question, args.claude, os.path.join(args.out, "raw"), args.timeout,
                              args.model, args.effort, args.setting_sources, args.max_turns)
                if row["api_key_source"] not in (None, "none"):
                    print(f"billing source is {row['api_key_source']}, not the subscription; stopping", flush=True)
                    return 4
                failed = row["exit"] != "timeout" and not row["hit_turn_limit"] and (
                    not row["result_seen"] or row["is_error"] or row["exit"] != 0)
                if failed:
                    print(f"{arm} {question['id']} r{rep}: run failed (exit {row['exit']}, subtype {row['subtype']}); "
                          f"stopping without recording it", flush=True)
                    return 5
                spent += row["tokens_total"]
                key = (arm, question["id"])
                largest[key] = max(largest.get(key, 0), row["tokens_total"])
                with open(rows_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(f"{arm} {row['id']} r{rep}: exit {row['exit']} {row['seconds']}s tools {row['tool_calls']} "
                      f"turns {row['turns']}{' CUT' if row['hit_turn_limit'] else ''} "
                      f"tokens {row['tokens_total']:,} (total {spent:,})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
