"""Session-stream tasting runner (D25, D26, D28) for a food whose claim is about later sessions.

Every arm owns one persistent copy of the corpus repository. The frozen tasks run in their frozen order,
one fresh `claude -p` session per task, in the same copy, so whatever a food learns from earlier
sessions (its own state, files it writes under .claude/) carries over, exactly as it would for a person
working in that repository. Before each session the code is reset to the base commit (`.venv` and
`.claude/` are kept), so every task starts from the same code in every arm and pairs stay comparable.

After a session the arm's copy is graded mechanically, before the next one starts: tests/ is restored to
the base commit (an agent's own test edits do not count), the task's hidden test is written as
tests/test_hidden_<id>.py, and the whole suite runs with the project's interpreter. Grading never sees
the arm name; the tests decide.

Changes against ../codemap-erpnext-confirm/taste_run.py:
- coding sessions, not read-only questions: Claude Code's default tool set in every arm (so a food that
  prunes tools has tools to prune), `--permission-mode acceptEdits` and Bash allowed;
- sessions are persisted (a food that learns from finished sessions reads Claude Code's own logs);
- `--setting-sources project,local` by default (a food may write the local settings file);
- tokens: all models in the result's `modelUsage`, plus the food's own model calls, read from the
  side-call log that sidecall_shim.py writes (arm key "sidecall_log"); effective tokens use the food's
  own weights (input 1, cache read 0.10, cache write 1.25, output 5);
- an arm may set "wait_for" (an env var value) to wait, after its session, until the detached
  processes the food spawned at session end (its `fold`) have exited, found by PID through /proc;
- an arm may set "plugin_required" or "plugin_forbidden"; an init event that disagrees stops the
  runner unrecorded (exit 6), as a wrong billing source does (exit 4);
- the arm order alternates by task (t01 N,T; t02 T,N; ...) when --alternate is given;
- the budget guard estimates the next pair from the largest pair so far.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

PROMPT = """You are working in the repository in the current directory.

{task}

Make the change in the source code and verify it with the project's tests. Do not commit."""

WEIGHTS = {"inputTokens": 1.0, "cacheReadInputTokens": 0.10, "cacheCreationInputTokens": 1.25,
           "outputTokens": 5.0}


def sh(argv, cwd, timeout=600, env=None):
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL, env=env)
    return done.returncode, done.stdout, done.stderr


def reset(arm_dir, base):
    sh(["git", "reset", "-q", "--hard", base], arm_dir)
    sh(["git", "clean", "-qfdx", "-e", ".venv", "-e", ".claude"], arm_dir)


def model_usage_totals(model_usage):
    raw, eff, cost = 0, 0.0, 0.0
    for usage in (model_usage or {}).values():
        for key, weight in WEIGHTS.items():
            value = int(usage.get(key) or 0)
            raw += value
            eff += weight * value
        cost += float(usage.get("costUSD") or 0)
    return raw, round(eff, 1), round(cost, 6)


def usage_totals(usage):
    """Fallback when a result has no modelUsage: the snake_case usage block."""
    names = {"input_tokens": "inputTokens", "cache_read_input_tokens": "cacheReadInputTokens",
             "cache_creation_input_tokens": "cacheCreationInputTokens", "output_tokens": "outputTokens"}
    return model_usage_totals({"_": {names[k]: v for k, v in (usage or {}).items() if k in names}})


def food_pids(marker):
    """PIDs of our own processes whose environment holds `marker` (KEY=VALUE) and that are not
    the runner itself; read from /proc, never by matching command lines."""
    found = []
    needle = marker.encode()
    for name in os.listdir("/proc"):
        if not name.isdigit() or int(name) == os.getpid():
            continue
        try:
            with open(f"/proc/{name}/environ", "rb") as handle:
                if needle in handle.read().split(b"\0"):
                    with open(f"/proc/{name}/cmdline", "rb") as cmd:
                        found.append((int(name), cmd.read().replace(b"\0", b" ").decode("utf-8", "replace")[:200]))
        except OSError:
            continue
    return found


def wait_food(marker, limit):
    """Wait until no process carrying `marker` is alive, except the food's long-lived pending-list
    waiter (`toolprune apply-pending`), which is recorded and left alone."""
    started = time.time()
    while True:
        alive = [(pid, cmd) for pid, cmd in food_pids(marker) if "apply-pending" not in cmd]
        if not alive:
            return round(time.time() - started, 1), []
        if time.time() - started > limit:
            return round(time.time() - started, 1), [cmd for _, cmd in alive]
        time.sleep(2)


def read_sidecalls(path, consumed):
    """Side-call log lines after index `consumed`: (entries, new consumed index)."""
    if not path or not os.path.exists(path):
        return [], consumed
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    entries = []
    for line in lines[consumed:]:
        try:
            entries.append(json.loads(line))
        except ValueError:
            entries.append({"unparsed": True})
    return entries, len(lines)


def grade(arm_dir, base, task, python, timeout):
    """Hidden test plus the whole suite, against the agent's source changes only."""
    sh(["git", "checkout", "-q", base, "--", "tests"], arm_dir)
    sh(["git", "clean", "-qfdx", "--", "tests"], arm_dir)
    hidden = os.path.join(arm_dir, "tests", f"test_hidden_{task['id']}.py")
    with open(hidden, "w", encoding="utf-8") as handle:
        handle.write(task["hidden_test"])
    env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "PATH": "/usr/bin:/bin"}
    flags = ["-q", "-p", "no:cacheprovider", "-rf", "--no-header"]
    code_h, out_h, _ = sh([python, "-m", "pytest", *flags, os.path.relpath(hidden, arm_dir)], arm_dir, timeout, env)
    code_s, out_s, _ = sh([python, "-m", "pytest", *flags, "tests"], arm_dir, timeout, env)
    failed = [line.split(" ", 1)[1].split(" - ")[0] for line in out_s.splitlines() if line.startswith("FAILED ")]
    tail = (out_s.strip().splitlines() or [""])[-1][:200]
    return {"hidden_pass": code_h == 0, "suite_exit": code_s, "suite_tail": tail,
            "suite_failed_other": sorted(f for f in failed if "test_hidden_" not in f)}


def run_one(arm, spec, task, args, position):
    env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "TERM": "dumb", "DISABLE_AUTOUPDATER": "1",
           "PATH": ":".join(spec.get("path_prepend", []) + [os.path.dirname(args.claude), "/usr/bin", "/bin"])}
    env.update(spec.get("env", {}))
    argv = [args.claude, "-p", PROMPT.format(task=task["prompt"]), "--output-format", "stream-json", "--verbose",
            "--permission-mode", "acceptEdits", "--allowedTools", "Bash", "--strict-mcp-config",
            "--setting-sources", args.setting_sources]
    if args.model:
        argv += ["--model", args.model]
    if args.effort:
        argv += ["--effort", args.effort]
    if args.max_turns:
        argv += ["--max-turns", str(args.max_turns)]
    reset(spec["dir"], args.base)
    started = time.time()
    try:
        done = subprocess.run(argv, cwd=spec["dir"], env=env, capture_output=True, text=True,
                              timeout=args.timeout, stdin=subprocess.DEVNULL)
        stdout, code = done.stdout, done.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        code = "timeout"
    seconds = round(time.time() - started, 1)
    raw = os.path.join(args.out, "raw", f"{arm}-{task['id']}.jsonl")
    with open(raw, "w", encoding="utf-8") as handle:
        handle.write(stdout)
    row = {"arm": arm, "id": task["id"], "position": position, "exit": code, "seconds": seconds,
           "api_key_source": None, "model": None, "plugins": [], "tools_loaded": None, "tools": {},
           "bash_count": 0, "test_runs": 0, "hook_messages": [], "usage": {}, "modelUsage": {},
           "cost_usd": None, "turns": None, "is_error": None, "subtype": None, "result_seen": False,
           "hit_turn_limit": False, "session_id": None}
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
            row["tools_loaded"] = sorted(event.get("tools") or [])
            row["session_id"] = event.get("session_id")
        elif kind == "system" and event.get("subtype") in ("hook_response", "hook_started"):
            text = str(event.get("output") or event.get("stdout") or "")
            if "TokenEconomizer" in text:
                row["hook_messages"].append(text[:300])
        elif kind == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    row["tools"][block["name"]] = row["tools"].get(block["name"], 0) + 1
                    if block["name"] == "Bash":
                        row["bash_count"] += 1
                        command = str(block.get("input", {}).get("command", ""))
                        if "pytest" in command or "unittest" in command:
                            row["test_runs"] += 1
        elif kind == "result":
            row["usage"] = event.get("usage", {}) or {}
            row["modelUsage"] = event.get("modelUsage", {}) or {}
            row["cost_usd"] = event.get("total_cost_usd")
            row["turns"] = event.get("num_turns")
            row["is_error"] = event.get("is_error")
            row["subtype"] = event.get("subtype")
            row["result_seen"] = True
    row["hit_turn_limit"] = row["subtype"] == "error_max_turns"
    if row["modelUsage"]:
        row["tokens_total"], row["effective_tokens"], row["model_cost_usd"] = model_usage_totals(row["modelUsage"])
    else:
        row["tokens_total"], row["effective_tokens"], row["model_cost_usd"] = usage_totals(row["usage"])
    row["tool_calls"] = sum(row["tools"].values())
    return row


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--arms", required=True)
    parser.add_argument("--order", default="N,T")
    parser.add_argument("--alternate", action="store_true")
    parser.add_argument("--ids", default="", help="comma-separated task ids, in stream order")
    parser.add_argument("--base", required=True, help="base commit of the corpus")
    parser.add_argument("--claude", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--budget", type=int, default=10_000_000)
    parser.add_argument("--timeout", type=int, default=1500)
    parser.add_argument("--grade-timeout", type=int, default=600)
    parser.add_argument("--wait-limit", type=int, default=900)
    parser.add_argument("--model", default="")
    parser.add_argument("--effort", default="")
    parser.add_argument("--setting-sources", default="project,local")
    parser.add_argument("--max-turns", type=int, default=0)
    args = parser.parse_args(argv)
    tasks = {t["id"]: t for t in json.load(open(args.tasks, encoding="utf-8"))["tasks"]}
    ids = args.ids.split(",") if args.ids else list(tasks)
    arms = json.load(open(args.arms, encoding="utf-8"))
    order = args.order.split(",")
    os.makedirs(os.path.join(args.out, "raw"), exist_ok=True)
    os.makedirs(os.path.join(args.out, "diffs"), exist_ok=True)
    rows_path = os.path.join(args.out, "rows.jsonl")
    state_path = os.path.join(args.out, "sidecall_state.json")
    consumed = json.load(open(state_path)) if os.path.exists(state_path) else {}
    done_keys, spent, pair = set(), 0, {}
    if os.path.exists(rows_path):
        for line in open(rows_path, encoding="utf-8"):
            row = json.loads(line)
            done_keys.add((row["arm"], row["id"]))
            spent += row["tokens_total"] + row.get("sidecall_tokens_total", 0)
            pair[row["id"]] = pair.get(row["id"], 0) + row["tokens_total"] + row.get("sidecall_tokens_total", 0)
    for position, task_id in enumerate(ids, start=1):
        task = tasks[task_id]
        rep_order = order[(position - 1) % len(order):] + order[:(position - 1) % len(order)] if args.alternate else order
        todo = [arm for arm in rep_order if (arm, task_id) not in done_keys]
        if not todo:
            continue
        estimate = max(pair.values() or [0]) * len(todo) / len(order)
        if spent >= args.budget or spent + estimate > args.budget:
            print(f"budget guard: {spent:,} spent, next pair needs about {estimate:,.0f}; not starting {task_id}", flush=True)
            return 3
        for arm in todo:
            spec = arms[arm]
            row = run_one(arm, spec, task, args, position)
            if row["api_key_source"] not in (None, "none"):
                print(f"billing source is {row['api_key_source']}, not the subscription; stopping", flush=True)
                return 4
            failed = row["exit"] != "timeout" and not row["hit_turn_limit"] and (
                not row["result_seen"] or row["is_error"] or row["exit"] != 0)
            if failed:
                print(f"{arm} {task_id}: run failed (exit {row['exit']}, subtype {row['subtype']}); "
                      f"stopping without recording it", flush=True)
                return 5
            plugins = set(row["plugins"])
            if spec.get("plugin_required") and spec["plugin_required"] not in plugins:
                print(f"{arm} {task_id}: init lacks plugin {spec['plugin_required']}; stopping", flush=True)
                return 6
            if spec.get("plugin_forbidden") and spec["plugin_forbidden"] in plugins:
                print(f"{arm} {task_id}: init has forbidden plugin {spec['plugin_forbidden']}; stopping", flush=True)
                return 6
            row["food_wait_s"], row["food_still_running"] = (
                wait_food(spec["wait_for"], args.wait_limit) if spec.get("wait_for") else (0, []))
            entries, consumed[arm] = read_sidecalls(spec.get("sidecall_log"), consumed.get(arm, 0))
            totals = [model_usage_totals(e.get("modelUsage")) if e.get("modelUsage") else usage_totals(e.get("usage"))
                      for e in entries]
            row["sidecalls"] = [{"model_arg": e.get("model_arg"), "exit": e.get("exit"), "seconds": e.get("seconds"),
                                 "tokens_total": t[0], "effective_tokens": t[1], "cost_usd": e.get("cost_usd"),
                                 "result_seen": e.get("result_seen")} for e, t in zip(entries, totals)]
            row["sidecall_tokens_total"] = sum(t[0] for t in totals)
            row["sidecall_effective_tokens"] = round(sum(t[1] for t in totals), 1)
            row["sidecall_cost_usd"] = round(sum(float(e.get("cost_usd") or 0) for e in entries), 6)
            diff = sh(["git", "diff", "--stat"], spec["dir"])[1] + sh(["git", "status", "--short"], spec["dir"])[1]
            full = sh(["git", "diff"], spec["dir"])[1]
            with open(os.path.join(args.out, "diffs", f"{arm}-{task_id}.diff"), "w", encoding="utf-8") as handle:
                handle.write(full)
            row["diff_stat"] = diff[-600:]
            row["grade"] = grade(spec["dir"], args.base, task, os.path.join(spec["dir"], ".venv", "bin", "python"),
                                 args.grade_timeout)
            reset(spec["dir"], args.base)
            spent += row["tokens_total"] + row["sidecall_tokens_total"]
            pair[task_id] = pair.get(task_id, 0) + row["tokens_total"] + row["sidecall_tokens_total"]
            with open(rows_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            with open(state_path, "w") as handle:
                json.dump(consumed, handle)
            done_keys.add((arm, task_id))
            print(f"{arm} {task_id} p{position}: exit {row['exit']} {row['seconds']}s turns {row['turns']}"
                  f"{' CUT' if row['hit_turn_limit'] else ''} tools {row['tool_calls']} "
                  f"tokens {row['tokens_total']:,} eff {row['effective_tokens']:,.0f} "
                  f"side {row['sidecall_tokens_total']:,} hidden {'PASS' if row['grade']['hidden_pass'] else 'FAIL'} "
                  f"suite-other-fail {len(row['grade']['suite_failed_other'])} (total {spent:,})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
