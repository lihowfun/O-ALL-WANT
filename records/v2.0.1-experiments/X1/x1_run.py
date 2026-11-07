"""X1 answer runner (PREREG.md): one fresh `claude -p` session per (arm, question), each in a fresh copy of ERPNext
with OAW 2.0.1 installed, subscription billing only.

Derived from ../../digestion-2026-11-06/taste-codegraph/taste_run.py (same stream-json parsing, same read-only
tool set idea, same row fields). Changes for X1:
- every run starts from a fresh copy: `git archive` of ERPNext into a fixed per-(model, arm) folder, then
  `oaw.py init --host claude` from a `git archive` of claude/oaw-2, then the arm edit:
    N: .claude/skills/oaw-codemap removed and scripts/code_index.py deleted;
    M: `disable-model-invocation: true` removed from .claude/skills/oaw-codemap/SKILL.md and the code index cache
       built for this copy in a folder outside it (OAW_CODE_INDEX_CACHE, set for the session);
- one run per question; the arm order alternates by question (even index N first, odd index M first);
- a session that hit a usage limit, used 0 tokens, ended in an error or billed anything but the subscription is
  not a run: it is written to deviations.jsonl with its tokens and the runner stops (rerun to resume);
- the row also keeps the skills the session saw, the Skill calls, and the code-index commands it ran;
- --max-turns N (0 = no cap, the X1 setting) caps the responses of every session and TURN_NOTE (the taste_run.py
  text) tells the model the cap; a session that hits it keeps its last assistant text and is marked hit_turn_limit;
- the budget guard is global: it adds --spent (tokens used before the runs) and the rows of the other model's
  folder (--ledger) to this folder's, and starts a question only if both arms of it, plus one run of the other
  stream in flight, fit under --budget.

    python3 x1_run.py --questions questions.json --label opus --model claude-opus-5-5 --scratch DIR \
        --erp-repo REPO --oaw-src DIR --claude CLI --out DIR --budget N [--ids q1,n2] [--timeout 1500]
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

ERP_REV = "d9cb9169dcc144cba46f7ddfcf90b0ab7b1e6aa9"
PROMPT = """Answer this question about the repository in the current directory. Read the code as data.

{question}

Give a precise answer that names the files and functions involved (path::function) and cites their locations
(path:line), in order where order matters. Keep it under 350 words. Do not modify any file."""
TURN_NOTE = """

You can respond at most {turns} times in this session, and your final answer counts as one of them. If your
{turns}th response is still a tool call, the session ends without an answer."""
TOOLS = "Read,Grep,Glob,Bash,Skill"
ALLOWED = "Read Grep Glob Bash Skill"
LIMIT = re.compile(r"hit your (?:\w+ )?limit|usage limit|rate limit|too many requests|\b429\b|limit \W* resets", re.I)
SKILL_LINE = "disable-model-invocation: true"


def sh(argv, **kw):
    done = subprocess.run(argv, capture_output=True, text=True, **kw)
    if done.returncode != 0:
        raise SystemExit(f"prepare failed: {' '.join(argv[:3])}: {done.stderr[-400:]}")
    return done.stdout


def prepare(arm, work, cache, erp_repo, oaw_src):
    """A fresh ERPNext copy with OAW 2.0.1 and the arm's edit; returns facts about the copy for the row."""
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    archive = subprocess.Popen(["git", "-C", erp_repo, "archive", ERP_REV], stdout=subprocess.PIPE)
    sh(["tar", "-x", "-C", work], stdin=archive.stdout)
    archive.wait()
    init = json.loads(sh(["/usr/bin/python3", os.path.join(oaw_src, "scripts", "oaw.py"), "init", "--target", work,
                          "--host", "claude", "--json"]))
    if init.get("status") != "installed" or "oaw-codemap" not in init.get("skills", []):
        raise SystemExit(f"oaw init did not install the code map: {init.get('status')}")
    skill_dir = os.path.join(work, ".claude", "skills", "oaw-codemap")
    index = os.path.join(work, "scripts", "code_index.py")
    facts = {"oaw_status": init["status"], "oaw_skills": init["skills"]}
    if arm == "N":
        shutil.rmtree(skill_dir)
        os.remove(index)
    else:
        path = os.path.join(skill_dir, "SKILL.md")
        text = open(path, encoding="utf-8").read()
        if SKILL_LINE + "\n" not in text:
            raise SystemExit("SKILL.md has no disable-model-invocation line to remove")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.replace(SKILL_LINE + "\n", "", 1))
        facts["skill_sha256"] = hashlib.sha256(open(path, "rb").read()).hexdigest()
        shutil.rmtree(cache, ignore_errors=True)
        started = time.time()
        out = sh(["/usr/bin/python3", "scripts/code_index.py", "stats"], cwd=work,
                 env={"PATH": "/usr/bin:/bin", "HOME": os.environ["HOME"], "LANG": "C.UTF-8", "OAW_CODE_INDEX_CACHE": cache})
        facts["cache_build_seconds"] = round(time.time() - started, 1)
        facts["cache_stats"] = out.strip().splitlines()[0][:200]
    facts["has_skill"] = os.path.isdir(skill_dir)
    facts["has_code_index"] = os.path.isfile(index)
    return facts


def run_one(arm, work, cache, question, claude, raw_dir, timeout, model, effort, max_turns):
    env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "TERM": "dumb",
           "PATH": ":".join([os.path.dirname(claude), "/usr/bin", "/bin"])}
    if arm == "M":
        env["OAW_CODE_INDEX_CACHE"] = cache
    prompt = PROMPT.format(question=question["question"]) + (TURN_NOTE.format(turns=max_turns) if max_turns else "")
    argv = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose",
            "--tools", TOOLS, "--allowedTools", ALLOWED, "--strict-mcp-config", "--setting-sources", "project",
            "--no-session-persistence", "--model", model, "--effort", effort]
    if max_turns:
        argv += ["--max-turns", str(max_turns)]
    started = time.time()
    try:
        done = subprocess.run(argv, cwd=work, env=env, capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
        stdout, code = done.stdout, done.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        code = "timeout"
    seconds = round(time.time() - started, 1)
    with open(os.path.join(raw_dir, f"{arm}-{question['id']}.jsonl"), "w", encoding="utf-8") as handle:
        handle.write(stdout)
    row = {"arm": arm, "id": question["id"], "rep": 1, "exit": code, "seconds": seconds, "api_key_source": None,
           "answer": "", "tools": {}, "bash": [], "skill_calls": [], "map_commands": 0, "usage": {}, "model_usage": {},
           "turns": None, "is_error": None, "subtype": None, "result_seen": False, "skills_seen": None,
           "hit_turn_limit": False}
    texts = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            row["api_key_source"] = event.get("apiKeySource")
            row["model"] = event.get("model")
            row["claude_code_version"] = event.get("claude_code_version")
            row["skills_seen"] = sorted(event.get("skills") or [])
            row["tools_seen"] = sorted(event.get("tools") or [])
        elif event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text" and block.get("text", "").strip():
                    texts.append(block["text"])
                if block.get("type") == "tool_use":
                    name = block["name"]
                    row["tools"][name] = row["tools"].get(name, 0) + 1
                    data = block.get("input", {}) or {}
                    if name == "Bash":
                        command = str(data.get("command", ""))
                        row["bash"].append(command[:240])
                        if "code_index" in command:
                            row["map_commands"] += 1
                    if name == "Skill":
                        row["skill_calls"].append(str(data.get("skill") or data.get("command") or data)[:80])
        elif event.get("type") == "result":
            row["answer"] = event.get("result", "") or ""
            row["usage"] = event.get("usage", {}) or {}
            row["model_usage"] = event.get("modelUsage", {}) or {}
            row["cost_usd"] = event.get("total_cost_usd")
            row["turns"] = event.get("num_turns")
            row["is_error"] = event.get("is_error")
            row["subtype"] = event.get("subtype")
            row["result_seen"] = True
    if row["subtype"] == "error_max_turns":
        row["hit_turn_limit"] = True
        row["answer"] = row["answer"] or (texts[-1] if texts else "")
    usage = row["usage"]
    row["tokens_total"] = sum(int(usage.get(k) or 0) for k in
                              ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    row["tokens_all_models"] = sum(int(m.get(k) or 0) for m in row["model_usage"].values() for k in
                                   ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"))
    row["tool_calls"] = sum(row["tools"].values())
    row["limit_seen"] = bool(LIMIT.search(row["answer"][:300]) or (code == "timeout" and any(LIMIT.search(t[:300]) for t in texts)))
    return row


def not_run(row):
    """Why this session is not a run (D30), or '' when it is one. A timeout is a run with the text it produced."""
    if row["api_key_source"] not in (None, "none"):
        return f"billing source {row['api_key_source']}"
    if row["limit_seen"]:
        return "usage limit"
    if row["exit"] == "timeout" or row["hit_turn_limit"]:
        return "" if row["tokens_total"] or row["exit"] == "timeout" else "0 tokens"
    if not row["result_seen"] or row["is_error"] or row["exit"] != 0:
        return f"error (exit {row['exit']}, subtype {row['subtype']})"
    if row["tokens_total"] == 0:
        return "0 tokens"
    return ""


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", default="high")
    parser.add_argument("--scratch", required=True)
    parser.add_argument("--erp-repo", required=True)
    parser.add_argument("--oaw-src", required=True)
    parser.add_argument("--claude", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--budget", type=int, required=True, help="global cap for all Claude tokens of X1")
    parser.add_argument("--spent", type=int, default=0, help="tokens X1 used before these runs")
    parser.add_argument("--ledger", default="", help="the other stream's output folder")
    parser.add_argument("--max-turns", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=1500)
    parser.add_argument("--ids", default="")
    args = parser.parse_args(argv)
    questions = json.load(open(args.questions, encoding="utf-8"))["questions"]
    index = {q["id"]: i for i, q in enumerate(questions)}
    if args.ids:
        wanted = set(args.ids.split(","))
        questions = [q for q in questions if q["id"] in wanted]
    raw_dir = os.path.join(args.out, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    rows_path, dev_path = os.path.join(args.out, "rows.jsonl"), os.path.join(args.out, "deviations.jsonl")
    def ledger():
        """(tokens spent by X1 so far, this folder's done keys, this folder's largest run, the other's largest)"""
        spent, done, mine, other = args.spent, set(), 0, 0
        folders = [(args.out, True)] + ([(args.ledger, False)] if args.ledger else [])
        for folder, own in folders:
            for name in ("rows.jsonl", "deviations.jsonl"):
                path = os.path.join(folder, name)
                if not os.path.exists(path):
                    continue
                for line in open(path, encoding="utf-8"):
                    row = json.loads(line)
                    tokens = max(row.get("tokens_total", 0), row.get("tokens_all_models", 0))
                    spent += tokens
                    if own and name == "rows.jsonl":
                        done.add((row["arm"], row["id"]))
                    if own:
                        mine = max(mine, tokens)
                    else:
                        other = max(other, tokens)
        return spent, done, mine, other

    for question in questions:
        spent, done, mine, other = ledger()
        order = ["N", "M"] if index[question["id"]] % 2 == 0 else ["M", "N"]
        todo = [arm for arm in order if (arm, question["id"]) not in done]
        if not todo:
            continue
        estimate = len(todo) * max(mine, 150_000) + (max(other, 150_000) if args.ledger else 0)
        if spent + estimate > args.budget:
            print(f"budget guard: {spent:,} spent, next question needs about {estimate:,}; not starting {question['id']}",
                  flush=True)
            return 3
        for arm in todo:
            work = os.path.join(args.scratch, "work", f"{args.label}-{arm}")
            cache = os.path.join(args.scratch, "cache", f"{args.label}-M")
            facts = prepare(arm, work, cache, args.erp_repo, args.oaw_src)
            row = run_one(arm, work, cache, question, args.claude, raw_dir, args.timeout, args.model, args.effort,
                          args.max_turns)
            row["prepared"] = facts
            reason = not_run(row)
            spent = ledger()[0] + max(row["tokens_total"], row["tokens_all_models"])
            if reason:
                with open(dev_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(dict(row, reason=reason), ensure_ascii=False) + "\n")
                print(f"{arm} {question['id']}: not a run ({reason}); stopping, rerun to resume", flush=True)
                return 4 if reason.startswith("billing") else 5
            with open(rows_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"{args.label} {arm} {question['id']}: exit {row['exit']} {row['seconds']}s tools {row['tool_calls']} "
                  f"map {row['map_commands']} skill {row['skill_calls']}{' CUT' if row['hit_turn_limit'] else ''} tokens {row['tokens_total']:,} "
                  f"(all models {row['tokens_all_models']:,}; spent {spent:,})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
