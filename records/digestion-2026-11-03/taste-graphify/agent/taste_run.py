"""Agent-level tasting runner (D25, D26): the same frozen questions, one fresh `claude -p` session per
(arm, question, repeat), each arm in its own copy of the repository. Subscription billing only.

Arms are defined in a JSON file: {"N": {"dir": "...", "tools": "Read,Grep,Glob", "allowed": "Read Grep Glob",
"path_prepend": []}, ...}. Every session is read-only: no Edit/Write tools exist in any arm. The raw
stream-json of each session stays local (native transcripts are not published); the summary keeps the
answer, tool-call counts, the Bash commands run, token usage and time.
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


def run_one(arm, spec, question, claude, raw_dir, timeout):
    env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "TERM": "dumb",
           "PATH": ":".join(spec.get("path_prepend", []) + [os.path.dirname(claude), "/usr/bin", "/bin"])}
    argv = [claude, "-p", PROMPT.format(question=question["question"]), "--output-format", "stream-json",
            "--verbose", "--tools", spec["tools"], "--allowedTools", spec["allowed"], "--strict-mcp-config"]
    started = time.time()
    try:
        done = subprocess.run(argv, cwd=spec["dir"], env=env, capture_output=True, text=True, timeout=timeout)
        stdout, code = done.stdout, done.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, code = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""), "timeout"
    seconds = round(time.time() - started, 1)
    raw = os.path.join(raw_dir, f"{arm}-{question['id']}-{question['_rep']}.jsonl")
    with open(raw, "w", encoding="utf-8") as handle:
        handle.write(stdout)
    row = {"arm": arm, "id": question["id"], "rep": question["_rep"], "exit": code, "seconds": seconds,
           "api_key_source": None, "answer": "", "tools": {}, "bash": [], "usage": {}, "cost_usd": None,
           "turns": None, "is_error": None}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            row["api_key_source"] = event.get("apiKeySource")
        elif event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
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
    args = parser.parse_args(argv)
    questions = json.load(open(args.questions, encoding="utf-8"))["questions"]
    if args.ids:
        wanted = set(args.ids.split(","))
        questions = [q for q in questions if q["id"] in wanted]
    arms = json.load(open(args.arms, encoding="utf-8"))
    order = args.order.split(",")
    os.makedirs(os.path.join(args.out, "raw"), exist_ok=True)
    rows_path = os.path.join(args.out, "rows.jsonl")
    spent = 0
    if os.path.exists(rows_path):
        for line in open(rows_path, encoding="utf-8"):
            spent += json.loads(line).get("tokens_total", 0)
    for rep in range(1, args.repeat + 1):
        for question in questions:
            for arm in order:
                if spent >= args.budget:
                    print(f"budget reached: {spent:,} tokens; stopping", flush=True)
                    return 3
                question = dict(question, _rep=rep)
                row = run_one(arm, arms[arm], question, args.claude, os.path.join(args.out, "raw"), args.timeout)
                if row["api_key_source"] not in (None, "none"):
                    print(f"billing source is {row['api_key_source']}, not the subscription; stopping", flush=True)
                    return 4
                spent += row["tokens_total"]
                with open(rows_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(f"{arm} {row['id']} r{rep}: exit {row['exit']} {row['seconds']}s tools {row['tool_calls']} "
                      f"tokens {row['tokens_total']:,} (total {spent:,})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
