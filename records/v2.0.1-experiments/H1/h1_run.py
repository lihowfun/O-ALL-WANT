#!/usr/bin/env python3
"""H1 runner: the same work units with and without a harness installed, in a sandbox, graded mechanically.

Arms: N (the corpus at its base commit), O (N plus the official OAW install, committed), L (N plus a two-line
policy file, committed). Cells: claude (Claude Code, Opus 5.5, effort high) and codex (Codex CLI, gpt-6.1-sol,
reasoning high). A unit is one or more sessions on the same working copy; the conversation is never resumed.

Every session and every grading step runs inside bubblewrap with its own PID namespace: the filesystem read-only,
/tmp, /home and the folders in H1_HIDE replaced by empty tmpfs, the working copy at /home/dev/proj and the unit's home
folder at /home/dev. The login file is bound, never copied. Grading has no network and no login, and runs on a fresh
copy of the base that receives nothing of the candidate's except its src/ folder.

Configuration is taken from the environment so that no local path is written into the records:
  H1_STATE  state root on a local disk (arms, runs, raw output)
  H1_BASE   the corpus at the base commit with its .venv built for /home/dev/proj
  H1_OAW    a checkout of the harness at the commit under test
  H1_HIDE   colon-separated folders to hide besides /tmp and /home (the projects and records folders at least)
  H1_RO     colon-separated folders to show again, read-only, at the same path (the host tools, the venv's runtime);
            `arms` copies each of them once into the state root, and every sandbox sees that copy, never the original
  H1_BIN    the folder holding the claude and codex executables (inside one of the H1_RO folders)

Subcommands: arms, budget, author, verify, solver, audit, freeze, launch, manifest, gate, run. See PREREG.md.
"""
import argparse
import fcntl
import glob
import hashlib
import importlib.util
import json
import os
import queue
import re
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ElementTree

sys.dont_write_bytecode = True  # loading the frozen oaw_mode.py must not leave a cache next to it

BASE_COMMIT = "49943b5a94413a530761350f04e896f76e8d620e"
HOME, WORK = "/home/dev", "/home/dev/proj"
GRADE = "/home/dev/grade"
PROMPT = ("You are working in the repository in the current directory.\n\n{task}\n\n"
          "Make the change in the source code and verify it with the project's tests. Do not commit.")
SOLVER_PROMPT = ("You are working in the repository in the current directory.\n\nThe maintainer sent the following "
                 "requests one after another. Carry out all of them, in order.\n\n{requests}\n\n"
                 "Make the changes in the source code and verify them with the project's tests. Do not commit.")
DISALLOWED = ("WebSearch,WebFetch,RemoteTrigger,PushNotification,ShareOnboardingGuide,CronCreate,CronDelete,CronList,"
              "ScheduleWakeup,SendMessage,ListAgents,EnterWorktree,ExitWorktree,Workflow")
L_POLICY = ("# Project guidance\n\n"
            "- Write decisions and facts that later work will need in NOTES.md at the repository root. If NOTES.md "
            "exists, read it before starting work.\n"
            "- For a large or risky change, have one fresh-context reviewer (a subagent with no view of this "
            "conversation) check the plan before you start and the diff and test results when you finish, and "
            "resolve the justified findings.\n")
MODELS = {"claude": "claude-opus-5-5", "codex": "gpt-6.1-sol"}
# The claude cell runs the primary arms only; the two-line control runs in the codex cell on classes B and C.
ARMS = {"claude": {"A": ["N1", "O", "N2"], "B": ["N1", "O", "N2"], "C": ["N1", "O", "N2"]},
        "codex": {"A": ["N1", "O", "N2"], "B": ["N1", "O", "L", "N2"], "C": ["N1", "O", "L", "N2"]}}
PRIMARY = ("N1", "N2", "O")
OFFSET = {"A": 0, "B": 4, "C": 8}
# First estimates of logical tokens per session in the claude cell; once a run of the same class and arm has been
# measured, the largest measured run is used instead.
ESTIMATE = {"A": {"N": 350_000, "O": 450_000, "L": 350_000},
            "B": {"N": 350_000, "O": 450_000, "L": 350_000},
            "C": {"N": 2_500_000, "O": 3_500_000, "L": 2_500_000}}
SESSION_SECONDS = 7200   # every session of every arm; a session that reaches it is cut and counts as an answer
CEILING = 8_000_000      # logical tokens in one claude session; the same treatment as the time limit
MAX_ATTEMPTS = 3         # attempts of one (cell, arm, unit) that may fail for infrastructure reasons
CAP = 30_000_000         # logical tokens the claude cell may spend, every attempt counted (D35)
CAP_DECISION = "D35"
RESERVE = 1.25           # the class C projection is multiplied by this before it is held against the cap
MAX_AUTHORS = 3          # counted author runs per class: the first and at most two supplements for missing types
# Amendment 2 (2026-11-11, before FREEZE.json): runner versions whose pre-freeze records (verification reports,
# solver rows, audit entries, calibration runs) stay valid. Nothing an earlier version checked is run again, so no
# check gets a second draw. Main runs and FREEZE.json bind the current runner only.
PRIOR_RUNNERS = frozenset({"706700a17af591b4d5a8f4e84ba745ea46488a29e40c71ec8796e70252fe20ad"})
FROZEN = ("PREREG.md", "AUTHOR_BRIEF_B.md", "AUTHOR_BRIEF_C.md", "h1_run.py", "h1_judge.py")
EDGE = r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])"  # a fact counts where it stands as a whole token
# Codex reports a usage limit only as text in its error events and on stderr; Claude's limit is read from the
# structured rate-limit and error fields of its stream, never from text.
LIMIT = re.compile(r"hit your (?:\w+ )?limit|usage limit reached|you've reached your usage limit|limit \W* resets \d", re.I)
SKILL_READ = re.compile(r"(?:\.agents|\.codex|\.claude)/skills/(?:\.system/)?([\w.-]+)/SKILL\.md")
LISTED_SKILL = re.compile(r"\(file: r\d+/([\w.-]+)/SKILL\.md\)")
BLOCKED = re.compile(r"Read-only file system|Permission denied|Operation not permitted")
SYSTEM_TOOLS = ("git", "bash", "python3", "bwrap", "timeout")
TYPES = {"B": ("explicit", "passing", "superseded", "handoff"), "C": ("large", "design")}
A_IDS = ("t01", "t04", "t09", "t12")  # class A: tasks 1, 4, 7 and 10 of the frozen tokeneconomizer bank
A_BANK_SHA256 = "0ecc8d51ba450cc6c622251739390b1985c7fac2b4de0b9fb8f09f588b4b37c6"
EVIDENCE = {"oaw": re.compile(r"oaw_mode|context_hub|code_index|oaw\.py|\.oaw/|\.agents/skills/|\.claude/skills/"
                              r"|oaw-(?:review|evidence|codemap|add)|egm-"),
            "notes": re.compile(r"NOTES\.md"),
            "memory": re.compile(r"\.claude/projects/[^\s\"']*/memory|MEMORY\.md|\.codex/memories"),
            "transcripts": re.compile(r"\.claude/projects/[^\s\"']*\.jsonl|\.codex/sessions|rollout-|thread_history")}

STATE = os.environ.get("H1_STATE", "")
BASE = os.environ.get("H1_BASE", "")
OAW = os.environ.get("H1_OAW", "")
HIDE = [p for p in os.environ.get("H1_HIDE", "").split(":") if p]
SHOW = [p for p in os.environ.get("H1_RO", "").split(":") if p]
BIN = os.environ.get("H1_BIN", "")


# ---------------------------------------------------------------- sandbox

def snapshot(index):
    """The copy of the H1_RO folder with this index that `arms` made in the state root."""
    return os.path.join(STATE, "tools", str(index))


def in_snapshot(path):
    """A path under one of the H1_RO folders, moved into that folder's copy in the state root."""
    for index, shown in enumerate(SHOW):
        if path == shown or path.startswith(shown + os.sep):
            return snapshot(index) + path[len(shown):]
    raise SystemExit(f"{path} is not inside a folder of H1_RO")


def sandbox(work, home, host, argv, *, net=True, extra=(), prepare=True):
    """argv wrapped so that only `work`, `home` and the folders in `extra` are writable and nothing else of the
    user's is visible, in a PID namespace of its own. `host` selects the login file to bind (None: no login).
    Each H1_RO folder is shown read-only at its own path, but with the content of its copy in the state root, so
    that a change to the original (an update of a CLI, a new cache file) cannot reach a run."""
    real = os.path.expanduser("~")
    wrap = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--tmpfs", "/home"]
    for hidden in HIDE:
        wrap += ["--tmpfs", hidden]
    for index, shown in enumerate(SHOW):
        if prepare and not os.path.isdir(snapshot(index)):
            raise SystemExit(f"no copy of H1_RO[{index}] in the state root; run `arms` first")
        wrap += ["--ro-bind", snapshot(index), shown]
    wrap += ["--bind", home, HOME] if home else ["--dir", HOME]
    wrap += ["--bind", work, WORK]
    if host == "claude":
        if prepare:
            os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
        wrap += ["--bind", os.path.join(real, ".claude", ".credentials.json"), f"{HOME}/.claude/.credentials.json"]
    elif host == "codex":
        if prepare:
            os.makedirs(os.path.join(home, ".codex"), exist_ok=True)
        wrap += ["--bind", os.path.join(real, ".codex", "auth.json"), f"{HOME}/.codex/auth.json"]
    for mode, source, target in extra:
        wrap += [mode, source, target]
    if not net:
        wrap += ["--unshare-net"]
    return wrap + ["--chdir", WORK, "--die-with-parent", "--unshare-ipc", "--unshare-pid", *argv]


def environment(tools=True):
    return {"HOME": HOME, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TERM": "dumb", "DISABLE_AUTOUPDATER": "1",
            "VIRTUAL_ENV": f"{WORK}/.venv",
            "PATH": f"{WORK}/.venv/bin:/usr/bin:/bin" + (f":{BIN}" if tools and BIN else ""),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_AUTHOR_NAME": "dev",
            "GIT_AUTHOR_EMAIL": "dev@example.invalid", "GIT_COMMITTER_NAME": "dev",
            "GIT_COMMITTER_EMAIL": "dev@example.invalid"}


def offline(work, script, *, io=None, timeout=2400):
    """A shell script in the working copy with no network, no login and an empty home (grading, git queries)."""
    extra = [("--bind", io, GRADE)] if io else []
    try:
        done = subprocess.run(sandbox(work, None, None, ["/bin/bash", "-c", script], net=False, extra=extra),
                              env=environment(tools=False), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    return done.returncode, done.stdout, done.stderr


def stream(argv, env, stdin_text, timeout, watch=None, tee=None):
    """Run argv, returning (stdout, stderr, exit code or the reason it was stopped). `watch` sees each stdout line
    and returns a reason to stop the run, or nothing. With `tee`, every stdout line is also written to that file
    and flushed as it arrives, so that the usage of an interrupted session can be recovered from it."""
    proc = subprocess.Popen(argv, env=env, stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    out, err, lines = [], [], queue.Queue()
    copy = open(tee, "w", encoding="utf-8") if tee else None

    def pump(pipe, sink, forward):
        for line in pipe:
            sink.append(line)
            if forward:
                if copy:
                    copy.write(line)
                    copy.flush()
                lines.put(line)

    readers = [threading.Thread(target=pump, args=(proc.stdout, out, True), daemon=True),
               threading.Thread(target=pump, args=(proc.stderr, err, False), daemon=True)]
    for reader in readers:
        reader.start()
    if stdin_text is not None:
        try:
            proc.stdin.write(stdin_text)
            proc.stdin.close()
        except BrokenPipeError:
            pass
    deadline, stopped = time.time() + timeout, ""
    while True:
        try:
            line = lines.get(timeout=1)
        except queue.Empty:
            line = None
        if line and watch and not stopped:
            stopped = watch(line) or ""
        if not stopped and time.time() > deadline:
            stopped = "timeout"
        if stopped:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(proc.pid, sig)
                except ProcessLookupError:
                    break
                try:
                    proc.wait(timeout=15)
                    break
                except subprocess.TimeoutExpired:
                    continue
            break
        if proc.poll() is not None and lines.empty():
            break
    for reader in readers:
        reader.join(timeout=15)
    if copy:
        copy.close()
    return "".join(out), "".join(err), stopped or proc.returncode


# ---------------------------------------------------------------- hosts

LOGICAL = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
NONCACHE = ("input_tokens", "output_tokens", "cache_creation_input_tokens")


def evidence(row, text):
    for name, pattern in EVIDENCE.items():
        if pattern.search(text):
            row["evidence"][name] = row["evidence"].get(name, 0) + 1


def events(lines):
    """The JSON objects among the lines of a stream; anything else is skipped."""
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            yield event


def claude_usage(lines):
    """(logical, non-cache) tokens of a Claude stream. A message's usage is repeated on each of its blocks, so it is
    taken once per message id. Used on a finished stream and on the partial raw file of an interrupted one."""
    usage = {}
    for event in events(line for line in lines if '"usage"' in line):
        message = event.get("message") or {}
        if isinstance(message, dict) and message.get("id") and isinstance(message.get("usage"), dict):
            usage[message["id"]] = message["usage"]
    return (sum(int(u.get(k) or 0) for u in usage.values() for k in LOGICAL),
            sum(int(u.get(k) or 0) for u in usage.values() for k in NONCACHE))


def model_ok(asked, actual):
    """The model a session actually ran on is the one asked for: the same name, or that name with a date suffix."""
    return bool(actual) and re.fullmatch(re.escape(asked) + r"(?:-\d{8})?", str(actual)) is not None


def claude_argv(prompt, model):
    return [os.path.join(BIN, "claude"), "-p", prompt, "--output-format", "stream-json", "--verbose", "--model", model,
            "--effort", "high", "--permission-mode", "bypassPermissions", "--setting-sources", "project",
            "--strict-mcp-config", "--disallowedTools", DISALLOWED]


def codex_argv(model, mode="workspace-write"):
    return [os.path.join(BIN, "codex"), "exec", "--json", "--model", model, "-c", 'model_reasoning_effort="high"',
            "--sandbox", mode, "--skip-git-repo-check", "--ignore-user-config", "--cd", WORK, "-"]


def run_claude(work, home, prompt, timeout, model, raw_dir, tag, allow=None):
    """One Claude Code session; its stdout goes to <raw_dir>/<tag>.jsonl as it arrives. `allow`: logical tokens this
    session may still use before the cell's cap; past it the session is stopped. A usage limit is read only from the
    stream's structured fields: a rejected rate-limit event, a main-thread message whose error is rate_limit, or an
    error result with status 429."""
    argv = claude_argv(prompt, model)
    usage = {}

    def watch(line):
        if '"usage"' not in line:
            return None
        for event in events([line]):
            message = event.get("message") or {}
            if isinstance(message, dict) and message.get("id") and isinstance(message.get("usage"), dict):
                usage[message["id"]] = sum(int(message["usage"].get(k) or 0) for k in LOGICAL)
        seen = sum(usage.values())
        if allow is not None and seen > allow:
            return "budget cap"
        return "token ceiling" if seen > CEILING else None

    started = time.time()
    stdout, stderr, code = stream(sandbox(work, home, "claude", argv), environment(), None, timeout, watch,
                                  tee=os.path.join(raw_dir, f"{tag}.jsonl"))
    row = {"exit": code, "seconds": round(time.time() - started, 1), "tools": {}, "skills": None, "agents": 0,
           "evidence": {}, "blocked": None, "stderr_tail": stderr[-400:], "limit_seen": False, "init_model": None,
           "root_models": [], "model": None, "api_key_source": None}
    final, roots, skills, blocked, init, missing = "", set(), [], 0, False, False
    for event in events(stdout.splitlines()):
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            init = True
            row["api_key_source"], row["init_model"] = event.get("apiKeySource"), event.get("model")
            row["version"] = event.get("claude_code_version")
            row["listed_skills"] = sorted(str(s) for s in event.get("skills") or [])
            row["listed_tools"] = sorted(str(t) for t in event.get("tools") or [])
            row["listed_agents"] = sorted(str(a) for a in event.get("agents") or [])
            row["mcp_servers"] = len(event.get("mcp_servers") or [])
            row["permission_mode"] = event.get("permissionMode")
        elif kind == "rate_limit_event":
            info = event.get("rate_limit_info") or {}
            if isinstance(info, dict):
                row["rate_limit"] = {k: info.get(k) for k in ("status", "rateLimitType", "utilization", "resetsAt")}
                if info.get("status") == "rejected":
                    row["limit_seen"] = True
        elif kind == "assistant":
            message = event.get("message") or {}
            main = event.get("parent_tool_use_id") is None
            if main and event.get("error") == "rate_limit":
                row["limit_seen"] = True
            if main and message.get("model") != "<synthetic>":
                if message.get("model"):
                    roots.add(str(message["model"]))
                else:
                    missing = True
            for block in message.get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name, payload = block.get("name", ""), block.get("input") or {}
                text = json.dumps(payload)
                row["tools"][name] = row["tools"].get(name, 0) + 1
                if name == "Skill":
                    skills.append(str(payload.get("skill", "")))
                skills += SKILL_READ.findall(text)
                if name in ("Task", "Agent"):
                    row["agents"] += 1
                evidence(row, text)
        elif kind == "user":
            content = (event.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    text = block.get("content")
                    blocked += bool(BLOCKED.search(text if isinstance(text, str) else json.dumps(text)))
        elif kind == "result":
            final = str(event.get("result", "") or "")
            row["result_seen"], row["is_error"], row["subtype"] = True, event.get("is_error"), event.get("subtype")
            row["api_error_status"] = event.get("api_error_status")
            if event.get("is_error") and event.get("api_error_status") == 429:
                row["limit_seen"] = True
            models = event.get("modelUsage") or {}
            row["models_used"] = sorted(models)
            row["tokens_total"] = sum(int(m.get(k) or 0) for m in models.values() for k in (
                "inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"))
            row["tokens_noncache"] = sum(int(m.get(k) or 0) for m in models.values() for k in (
                "inputTokens", "outputTokens", "cacheCreationInputTokens"))
    if not row.get("tokens_total"):
        row["tokens_total"], row["tokens_noncache"] = claude_usage(stdout.splitlines())
        row["tokens_from"] = "stream (lower bound)"
    row["root_models"] = sorted(roots)
    row["root_model_missing"] = missing
    row["model"] = row["root_models"][0] if len(roots) == 1 and not missing else None
    # The 8M ceiling is enforced on the stream as it arrives; subagent usage that the stream does not show can push
    # the final total over it. Such a session is an answer like any other and is flagged, never rerun.
    row["over_ceiling"] = row["exit"] != "token ceiling" and (row.get("tokens_total") or 0) > CEILING
    if init:
        row["skills"], row["blocked"] = skills, blocked
    row["final"] = final
    return row


def login_check():
    """'chatgpt' when the Codex login file is a ChatGPT sign-in with no API key, otherwise what is wrong. Only key
    names and the non-secret sign-in mode are looked at; no value goes into a record."""
    try:
        data = json.load(open(os.path.join(os.path.expanduser("~"), ".codex", "auth.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return "login file unreadable"
    if not isinstance(data, dict):
        return "login file is not an object"
    if data.get("OPENAI_API_KEY"):
        return "an API key is set"
    if data.get("auth_mode") != "chatgpt":
        return f"sign-in mode {str(data.get('auth_mode'))[:20]}"
    if not isinstance(data.get("tokens"), dict) or not data["tokens"]:
        return "no sign-in tokens"
    return "chatgpt"


def rollout_tokens(path):
    last = None
    for line in open(path, encoding="utf-8", errors="replace"):
        if '"token_count"' in line:
            for event in events([line]):
                info = (event.get("payload") or {}).get("info") or {}
                last = info.get("total_token_usage") or last
    if not last:
        return 0, 0
    total = int(last.get("input_tokens") or 0) + int(last.get("output_tokens") or 0)
    return total, total - int(last.get("cached_input_tokens") or 0)


def tool_names(entries, prefix=""):
    """Names of the tools in a Codex tool list, namespaces spelled out (namespace.tool)."""
    names = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "")
        if isinstance(entry.get("tools"), list):
            names += tool_names(entry["tools"], f"{prefix}{name}.")
        elif name:
            names.append(prefix + name)
    return names


def rollout_facts(path):
    """What one Codex thread's rollout shows: its id, provider and models, the first turn's sandbox context (with the
    paths it keeps read-only), the skills and tools listed at startup (None when the rollout does not show them),
    the skill files its tool calls read, the text of those calls and how many tool outputs report a write that the
    sandbox blocked."""
    facts = {"thread": None, "provider": None, "models": [], "model_missing": 0, "context": None,
             "listed_skills": None, "listed_tools": None, "skill_reads": [], "tool_texts": [], "tool_items": 0,
             "blocked": 0}
    for event in events(open(path, encoding="utf-8", errors="replace")):
        payload = event.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        kind, item = event.get("type"), payload.get("type")
        if kind == "session_meta":
            facts["thread"], facts["provider"] = payload.get("id"), payload.get("model_provider")
        elif kind == "turn_context":
            if payload.get("model"):
                facts["models"].append(str(payload["model"]))
            else:
                facts["model_missing"] += 1
            if facts["context"] is None:
                policy = payload.get("file_system_sandbox_policy") or {}
                entries = policy.get("entries") if isinstance(policy, dict) else None
                facts["context"] = {key: payload.get(key) for key in (
                    "approval_policy", "sandbox_policy", "effort", "multi_agent_version")}
                facts["context"]["read_only"] = sorted(
                    str(entry["path"].get("path")) for entry in (entries if isinstance(entries, list) else [])
                    if isinstance(entry, dict) and entry.get("access") == "read"
                    and isinstance(entry.get("path"), dict) and entry["path"].get("type") == "path")
        elif item == "message" and payload.get("role") == "developer":
            text = " ".join(str(c.get("text", "")) for c in payload.get("content") or [] if isinstance(c, dict))
            if "<skills_instructions>" in text:
                facts["listed_skills"] = sorted(set(LISTED_SKILL.findall(text)))
        elif item == "additional_tools":
            facts["listed_tools"] = sorted(tool_names(payload.get("tools")))
        elif item in ("custom_tool_call", "function_call", "local_shell_call"):
            text = payload.get("input") or payload.get("arguments") or payload.get("action") or {}
            text = text if isinstance(text, str) else json.dumps(text)
            facts["tool_items"] += 1
            facts["tool_texts"].append(text)
            facts["skill_reads"] += SKILL_READ.findall(text)
        elif item in ("custom_tool_call_output", "function_call_output", "local_shell_call_output"):
            facts["blocked"] += bool(BLOCKED.search(json.dumps(payload.get("output"))))
    return facts


def run_codex(work, home, prompt, timeout, model, raw_dir, tag, mode="workspace-write"):
    """One Codex session; its stdout goes to <raw_dir>/<tag>.jsonl as it arrives and the rollouts it adds are kept
    in <raw_dir>/<tag>-rollouts. Model, provider, skills and tools are read from the root thread's rollout."""
    argv = codex_argv(model, mode)
    sessions = os.path.join(home, ".codex", "sessions")
    before = set(glob.glob(os.path.join(sessions, "**", "rollout-*.jsonl"), recursive=True))
    started = time.time()
    stdout, stderr, code = stream(sandbox(work, home, "codex", argv), environment(), prompt, timeout,
                                  tee=os.path.join(raw_dir, f"{tag}.jsonl"))
    row = {"exit": code, "seconds": round(time.time() - started, 1), "tools": {}, "skills": None, "agents": 0,
           "evidence": {}, "blocked": None, "api_key_source": login_check(), "stderr_tail": stderr[-400:],
           "provider": None, "root_models": [], "root_model_missing": False, "listed_skills": None,
           "listed_tools": None, "context": None, "over_ceiling": False}
    texts, errors, root_id = [], [], None
    parent = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    for event in events(stdout.splitlines()):
        kind = event.get("type")
        if kind == "thread.started":
            root_id = event.get("thread_id")
        elif kind == "item.completed":
            item = event.get("item") or {}
            if item.get("type") == "agent_message" and str(item.get("text", "")).strip():
                texts.append(str(item["text"]))
            elif item.get("type") and item.get("type") != "reasoning":
                row["tools"][item["type"]] = row["tools"].get(item["type"], 0) + 1
        elif kind == "turn.completed":
            row["result_seen"] = True
            for key in parent:
                parent[key] += int((event.get("usage") or {}).get(key) or 0)
        elif kind in ("turn.failed", "error"):
            errors.append(json.dumps(event)[:300])
    # Every rollout this session added to the unit's home belongs to it: the root thread and its descendants.
    keep = os.path.join(raw_dir, f"{tag}-rollouts")
    os.makedirs(keep, exist_ok=True)
    threads = []
    for path in sorted(set(glob.glob(os.path.join(sessions, "**", "rollout-*.jsonl"), recursive=True)) - before):
        copy = os.path.join(keep, os.path.basename(path))
        shutil.copyfile(path, copy)
        facts = rollout_facts(copy)
        facts["root"], facts["tokens"] = bool(root_id) and facts["thread"] == root_id, rollout_tokens(copy)
        threads.append(facts)
        for text in facts["tool_texts"]:
            evidence(row, text)
    root = [t for t in threads if t["root"]]
    if root:
        row["provider"], row["root_models"] = root[0]["provider"], sorted(set(root[0]["models"]))
        row["root_model_missing"] = bool(root[0]["model_missing"])
        row["context"], row["listed_skills"], row["listed_tools"] = (root[0]["context"], root[0]["listed_skills"],
                                                                     root[0]["listed_tools"])
        # A stream that reported tool items while no rollout shows a recognisable call: skill use is unknown.
        if sum(t["tool_items"] for t in threads) or not sum(row["tools"].values()):
            row["skills"] = [name for t in threads for name in t["skill_reads"]]
            row["blocked"] = sum(t["blocked"] for t in threads)
    row["model"] = row["root_models"][0] if len(row["root_models"]) == 1 and not row["root_model_missing"] else None
    row["models_used"] = sorted({m for t in threads for m in t["models"]})
    row["threads"] = len(threads)
    row["agents"] = sum(1 for t in threads if not t["root"])
    if root and root[0]["tokens"][0]:
        base, row["tokens_from"] = root[0]["tokens"], "rollouts (all threads of the session)"
    else:
        base = (parent["input_tokens"] + parent["output_tokens"],
                parent["input_tokens"] - parent["cached_input_tokens"] + parent["output_tokens"])
        row["tokens_from"] = "parent stream + other rollouts"
    row["tokens_total"] = base[0] + sum(t["tokens"][0] for t in threads if not t["root"])
    row["tokens_noncache"] = base[1] + sum(t["tokens"][1] for t in threads if not t["root"])
    row["final"] = texts[-1] if texts else ""
    row["errors"] = errors
    row["is_error"] = bool(errors) and not row.get("result_seen")
    row["limit_seen"] = bool(LIMIT.search(" ".join(errors) + " " + stderr[-600:]))
    return row


def not_run(row, cell, model):
    """Why a session does not count as run (D30), or an empty string. Only infrastructure reasons are listed here:
    a session cut at the time limit or the token ceiling is an answer and is graded as it stands. The order: the
    budget, the billing source (known without any output), a usage limit, no tokens, the provider, the exact root
    model, then errors."""
    if row["exit"] == "budget cap":
        return "budget cap"
    wanted = "none" if cell == "claude" else "chatgpt"
    if row.get("api_key_source") != wanted:
        return f"billing source {row.get('api_key_source')}"
    if row.get("limit_seen"):
        return "usage limit"
    if not row.get("tokens_total"):
        return "0 tokens"
    if cell == "codex" and row.get("provider") != "openai":
        return f"provider {row.get('provider')}"
    roots = row.get("root_models") or []
    if not roots or row.get("root_model_missing") or not all(model_ok(model, m) for m in roots):
        return f"model {','.join(roots) or 'missing'}" + (" (a root message without a model)"
                                                          if row.get("root_model_missing") else "")
    if row["exit"] in ("timeout", "token ceiling"):
        return ""
    if not row.get("result_seen") or row.get("is_error") or row["exit"] != 0:
        return f"error (exit {row['exit']}, subtype {row.get('subtype')})"
    return ""


# ---------------------------------------------------------------- state of a unit between sessions

def digest(path):
    total = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            total.update(block)
    return total.hexdigest()


def unit_digest(unit):
    return hashlib.sha256(json.dumps(unit, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def memory_files(home):
    """Files the host's own memory left in the unit's home (name, size, digest; never the login file)."""
    found = {}
    for pattern in (".claude/projects/*/memory/**", ".codex/memories/**"):
        for path in glob.glob(os.path.join(home, pattern), recursive=True):
            if os.path.isfile(path) and not os.path.islink(path):
                found[os.path.relpath(path, home)] = [os.path.getsize(path), digest(path)[:12]]
    return found


def fact_places(work, home, facts, limit=20):
    """Where the unit's fact strings are on disk (paths relative to the working copy or the home), as evidence of
    how a decision was carried. Files are read as bytes; links, the venv, git objects and login files are skipped."""
    needles = [str(f).encode() for f in facts if str(f)]
    places = []
    for label, root in (("work", work), ("home", home)):
        for base, dirs, names in os.walk(root):
            rel = os.path.relpath(base, root)
            dirs[:] = sorted(d for d in dirs if not (rel == "." and d in (".venv", ".git", "proj", ".cache")))
            for name in sorted(names):
                path = os.path.join(base, name)
                if name in (".credentials.json", "auth.json") or os.path.islink(path) or not os.path.isfile(path):
                    continue
                if os.path.getsize(path) > 50_000_000:
                    continue
                data = open(path, "rb").read()
                if any(needle in data for needle in needles):
                    places.append(f"{label}:{os.path.relpath(path, root)}")
    return places[:limit]


def changed_paths(work):
    code, out, _err = offline(work, "export GIT_OPTIONAL_LOCKS=0\n"
                                    "git status --porcelain --untracked-files=all | cut -c4- | head -200", timeout=120)
    return out.splitlines() if code == 0 else ["<git status failed>"]


# ---------------------------------------------------------------- grading

PYTEST = ".venv/bin/python -m pytest -q -p no:cacheprovider --no-header -rf"
RANK = {"passed": 0, "xfailed": 1, "skipped": 2, "failed": 3, "error": 4}


def hidden_name(unit):
    return "test_hidden_" + re.sub(r"\W", "_", unit["id"]) + ".py"


def safe_id(unit):
    """Unit ids become folder names; anything else than letters, digits, dot, dash and underscore is refused."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", str(unit.get("id", ""))):
        raise SystemExit(f"unit id {unit.get('id')!r} is not usable as a name")
    return unit["id"]


def junit(path):
    """Node id ('<classname>::<name>') -> passed, failed, error, skipped or xfailed, from a junit file; None when the
    file cannot be read. A node reported twice (a call and a teardown error) keeps its worst status."""
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError):
        return None
    nodes = {}
    for case in root.iter("testcase"):
        status = "passed"
        for child in case:
            found = {"error": "error", "failure": "failed"}.get(child.tag)
            if child.tag == "skipped":
                found = "xfailed" if child.get("type") == "pytest.xfail" else "skipped"
            if found and RANK[found] > RANK[status]:
                status = found
        node = f"{case.get('classname') or ''}::{case.get('name') or ''}"
        if node not in nodes or RANK[status] > RANK[nodes[node]]:
            nodes[node] = status
    return nodes


def hidden_cases(unit, nodes):
    """The hidden test's cases by function (function -> {case name: status}), and the nodes that are not plain
    functions of the hidden module (test methods, other modules)."""
    module = "tests." + hidden_name(unit)[:-3]
    mine, alien = {}, []
    for node, status in (nodes or {}).items():
        classname, name = node.split("::", 1)
        if classname == module:
            mine.setdefault(name.split("[", 1)[0], {})[name] = status
        else:
            alien.append(node)
    return mine, sorted(alien)


def only_plain(folder, names):
    """copytree filter: caches and anything that is not a file, a folder or a link stay behind."""
    skip = []
    for name in names:
        path = os.path.join(folder, name)
        if name == "__pycache__" or not (os.path.islink(path) or os.path.isfile(path) or os.path.isdir(path)):
            skip.append(name)
    return skip


def tree_digest(root):
    """One sha256 over everything in a folder, caches included: every folder, every link with its target, every
    file with its executable bits and content, and any other kind of entry, by sorted relative name."""
    total = hashlib.sha256()
    for base, dirs, names in os.walk(root):
        dirs.sort()
        for name in sorted(dirs + names):
            path = os.path.join(base, name)
            rel, mode = os.path.relpath(path, root), os.lstat(path).st_mode
            if stat.S_ISLNK(mode):
                total.update(f"L {rel} -> {os.readlink(path)}\n".encode())
            elif stat.S_ISDIR(mode):
                total.update(f"D {rel}\n".encode())
            elif stat.S_ISREG(mode):
                total.update(f"F {rel} {oct(mode & 0o111)} {digest(path)}\n".encode())
            else:
                total.update(f"S {rel} {oct(stat.S_IFMT(mode))}\n".encode())
    return total.hexdigest()


def tail(path):
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().strip().splitlines()
    except OSError:
        return ""
    return lines[-1][:200] if lines else ""


def remove_tree(path):
    """Remove a folder this runner created under the state root, and nothing else."""
    real, root = os.path.realpath(path), os.path.realpath(STATE)
    if not STATE or not real.startswith(root + os.sep) or real.count(os.sep) < root.count(os.sep) + 2:
        raise SystemExit(f"refusing to remove {path}")
    shutil.rmtree(real)


def baseline_path():
    return os.path.join(STATE, "arms", "suite_baseline.json")


def suite_baseline():
    """Status of every case of the existing suite on the base, as `arms` recorded it."""
    if not os.path.exists(baseline_path()):
        raise SystemExit("no suite baseline in the state root; run `arms` first")
    return json.load(open(baseline_path(), encoding="utf-8"))["cases"]


def number(path):
    try:
        return int(open(path).read().strip())
    except (OSError, ValueError):
        return None


def suite_on_base(out_dir):
    """The existing suite on a fresh copy of the N template: (exit code, node -> status or None)."""
    io, fresh = os.path.join(out_dir, "io"), os.path.join(out_dir, "proj")
    os.makedirs(io)
    shutil.copytree(arm_dir("N"), fresh, symlinks=True)
    offline(fresh, f"cd {WORK} || exit 90\n"
                   f"timeout 1500 {PYTEST} tests --junitxml={GRADE}/suite.xml > {GRADE}/suite.txt 2>&1\n"
                   f"echo $? > {GRADE}/suite.code", io=io)
    remove_tree(fresh)
    return number(os.path.join(io, "suite.code")), junit(os.path.join(io, "suite.xml"))


def design_note(unit):
    """The one design note a design unit's prompt names (docs/designs/<name>.md), or None."""
    sessions = unit.get("sessions") or []
    if unit.get("type") != "design" or not sessions:
        return None
    named = sorted(set(re.findall(r"docs/designs/[\w.-]+\.md", sessions[0])))
    return named[0] if len(named) == 1 else None


def grade(unit, work, out_dir, patch=None, ref=None, suite=True):
    """Grade the src/ folder of a working copy on a fresh copy of the base: the hidden test alone, then the existing
    suite. Nothing else of the candidate's reaches the graded tree. With `patch` (unit verification) the patch is
    first applied to a copy of `work`. With `ref`, the candidate's diff against that commit is kept as a record, in
    a folder the grading step never reads.

    A hidden function passes when every one of its cases passed and, for a frozen unit, the case names are exactly
    the frozen ones. The suite regresses when it exits non-zero or any case that passed on the base did not pass
    (missing, failed, errored, skipped or xfailed)."""
    base_cases = suite_baseline() if suite else None
    if os.path.isdir(out_dir):
        remove_tree(out_dir)
    io, record = os.path.join(out_dir, "io"), os.path.join(out_dir, "record")
    os.makedirs(io)
    os.makedirs(record)
    result = {"script_exit": None, "script_err": "", "error": "", "hidden_exit": None, "suite_exit": None,
              "suite_regression": None, "suite_failed": None, "suite_lost": None, "suite_lost_sample": [],
              "functions": {}, "nodes": {}, "collected": [], "alien": [], "items": {}, "passed": 0, "n": 0,
              "score": None, "recall": None, "suite_tail": "", "hidden_tail": ""}
    source = work
    if patch is not None:
        source = os.path.join(out_dir, "candidate")
        shutil.copytree(work, source, symlinks=True, ignore=shutil.ignore_patterns(".venv"))
        with open(os.path.join(record, "ref.patch"), "w", encoding="utf-8") as handle:
            handle.write(patch if patch.endswith("\n") else patch + "\n")
        code, _out, err = offline(source, f"git apply --check {GRADE}/ref.patch || exit 80\n"
                                          f"git apply {GRADE}/ref.patch || exit 81", io=record, timeout=300)
        if code:
            remove_tree(source)
            return dict(result, script_exit=code, script_err=err[-300:], error="the patch does not apply")
    if ref:
        offline(work, f"export GIT_OPTIONAL_LOCKS=0\ngit diff {ref} > {GRADE}/final.diff 2>&1\n"
                      f"git status --porcelain --untracked-files=all > {GRADE}/status.txt 2>&1", io=record, timeout=300)
    fresh = os.path.join(out_dir, "proj")
    shutil.copytree(arm_dir("N"), fresh, symlinks=True)
    remove_tree(os.path.join(fresh, "src"))
    candidate = os.path.join(source, "src")
    if os.path.isdir(candidate) and not os.path.islink(candidate):
        shutil.copytree(candidate, os.path.join(fresh, "src"), symlinks=True, ignore=only_plain)
    note = design_note(unit)  # a design unit's prompt asks for this one note; it is the only other file graded
    held = os.path.join(source, note) if note else ""
    inside = held and os.path.realpath(held).startswith(os.path.realpath(source) + os.sep)
    if inside and os.path.isfile(held) and not os.path.islink(held):
        os.makedirs(os.path.dirname(os.path.join(fresh, note)), exist_ok=True)
        shutil.copyfile(os.path.join(source, note), os.path.join(fresh, note))
    if patch is not None:
        remove_tree(source)
    with open(os.path.join(io, "hidden.py"), "w", encoding="utf-8") as handle:
        handle.write(unit["hidden_test"])
    name = hidden_name(unit)
    steps = [f"cd {WORK} || exit 90", f"cp {GRADE}/hidden.py tests/{name} || exit 93",
             f"timeout -k 30 600 {PYTEST} tests/{name} --junitxml={GRADE}/hidden.xml > {GRADE}/hidden.txt 2>&1",
             f"echo $? > {GRADE}/hidden.code", f"rm -f tests/{name}"]
    if suite:
        steps += [f"timeout -k 30 1500 {PYTEST} tests --junitxml={GRADE}/suite.xml > {GRADE}/suite.txt 2>&1",
                  f"echo $? > {GRADE}/suite.code"]
    code, _out, err = offline(fresh, "\n".join(steps), io=io)
    remove_tree(fresh)
    hidden_exit = number(os.path.join(io, "hidden.code"))
    suite_exit = number(os.path.join(io, "suite.code")) if suite else None
    if code == 124 and err == "timeout":  # the whole grading step outlived its limit: the candidate's outcome
        hidden_exit = 124 if hidden_exit is None else hidden_exit
        suite_exit = (124 if suite_exit is None else suite_exit) if suite else None
        code = 0
    cases, alien = hidden_cases(unit, junit(os.path.join(io, "hidden.xml")))
    frozen = unit.get("nodes")
    functions = unit.get("functions") or sorted(cases)

    def good(fn):
        seen = cases.get(fn) or {}
        if not seen or any(status != "passed" for status in seen.values()):
            return False
        return frozen is None or sorted(seen) == frozen.get(fn)

    passed = {fn: good(fn) for fn in functions}
    items = unit.get("items") or {fn: [fn] for fn in functions}
    met = {key: bool(members) and all(passed.get(fn, False) for fn in members) for key, members in items.items()}
    regression, lost, failed = None, [], None
    now = junit(os.path.join(io, "suite.xml")) if suite else None
    if suite and now is not None:
        lost = sorted(node for node, status in base_cases.items() if status == "passed" and now.get(node) != "passed")
        regression = suite_exit != 0 or bool(lost)
        failed = sum(1 for status in now.values() if status in ("failed", "error"))
    elif suite and suite_exit is not None:
        regression = True  # the suite ran but left no readable report (a timeout, a crash): it does not run
    recall = [fn for fn in functions if fn.startswith("test_recall_")]
    error = ""
    if code or hidden_exit is None or (suite and suite_exit is None):
        error = f"grading script exit {code}, hidden {hidden_exit}, suite {suite_exit}"
    return dict(result, script_exit=code, script_err=err[-300:], error=error, hidden_exit=hidden_exit,
                suite_exit=suite_exit, suite_regression=regression, suite_failed=failed,
                suite_lost=len(lost) if suite and now is not None else None, suite_lost_sample=lost[:5],
                functions=passed, nodes={fn: sorted(seen) for fn, seen in cases.items()}, collected=sorted(cases),
                alien=alien[:20], items=met, passed=sum(met.values()), n=len(met),
                score=(0.0 if regression else sum(met.values()) / len(met)) if met else None,
                recall=(all(passed[fn] for fn in recall) and not regression) if recall else None,
                suite_tail=tail(os.path.join(io, "suite.txt")), hidden_tail=tail(os.path.join(io, "hidden.txt")))


# ---------------------------------------------------------------- arms

def arm_dir(arm):
    return os.path.join(STATE, "arms", arm[0], "proj")


def arms_json():
    return json.load(open(os.path.join(STATE, "arms", "arms.json"), encoding="utf-8"))


def arm_facts(arm):
    """Commit, tree, uncommitted count and the content digest of the whole template (.git, .venv and ignored files
    included) as it is now. Every file of the template is copied into a run, so every file is in the digest."""
    code, out, err = offline(arm_dir(arm), "export GIT_OPTIONAL_LOCKS=0\ngit rev-parse HEAD && "
                             "git rev-parse 'HEAD^{tree}' && git status --porcelain | wc -l", timeout=300)
    if code:
        raise SystemExit(f"{arm}: cannot read the template: {err[-300:]}")
    commit, tree, dirty = out.strip().splitlines()[-3:]
    return {"commit": commit, "tree": tree, "uncommitted": int(dirty), "content_sha256": tree_digest(arm_dir(arm))}


def tools_facts():
    """Content digest of each copy of an H1_RO folder in the state root."""
    return [{"index": index, "content_sha256": tree_digest(snapshot(index))} for index in range(len(SHOW))]


def cmd_arms(_args):
    """Copy the H1_RO folders into the state root, build the three arm templates, and record the status of every
    case of the existing suite on the base (two runs that must agree). Every unit starts from a copy of a template."""
    if os.path.exists(os.path.join(STATE, "arms")) or os.path.exists(os.path.join(STATE, "tools")):
        raise SystemExit("arms already built; build into a fresh H1_STATE instead")
    if not any(BIN == shown or BIN.startswith(shown + os.sep) for shown in SHOW):
        raise SystemExit("H1_BIN must lie inside a folder of H1_RO, so that the copy covers both CLIs")
    for index, shown in enumerate(SHOW):
        shutil.copytree(shown, snapshot(index), symlinks=True)  # copy2 keeps modes and times
    out = {"base_commit": BASE_COMMIT, "arms": {}, "tools": tools_facts()}
    head = subprocess.run(["git", "-C", OAW, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", OAW, "status", "--porcelain", "--", "scripts", "templates"],
                           capture_output=True, text=True).stdout.strip()
    out["oaw_commit"], out["oaw_scripts_templates_clean"] = head, not dirty
    setup_home = os.path.join(STATE, "arms", "_home")
    os.makedirs(setup_home)
    commit = "git add -A && git commit -q -m {message!r} && "
    report = ("git rev-parse HEAD && git rev-parse 'HEAD^{tree}' && git status --porcelain | wc -l && "
              f"git diff --name-only {BASE_COMMIT} HEAD | wc -l && python3 --version")
    scripts = {"N": report,
               "O": f"python3 {HOME}/OAW/scripts/oaw.py init --target {WORK} --host both >&2 && "
                    + commit.format(message="Install OAW") + report,
               "L": f"cp {GRADE}/AGENTS.md AGENTS.md && printf '@AGENTS.md\\n' > CLAUDE.md && "
                    + commit.format(message="Add project guidance") + report}
    for arm, script in scripts.items():
        target = arm_dir(arm)
        os.makedirs(os.path.dirname(target))
        shutil.copytree(BASE, target, symlinks=True)
        io = os.path.join(STATE, "arms", arm, "io")
        os.makedirs(io)
        with open(os.path.join(io, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write(L_POLICY)
        extra = [("--bind", io, GRADE)] + ([("--ro-bind", OAW, f"{HOME}/OAW")] if arm == "O" else [])
        done = subprocess.run(sandbox(target, setup_home, None, ["/bin/bash", "-c", "set -e; " + script], net=False,
                                      extra=extra), env=environment(tools=False), capture_output=True, text=True)
        if done.returncode:
            raise SystemExit(f"{arm}: setup failed: {done.stderr[-600:]}")
        commit_id, tree, dirty_count, files, python = done.stdout.strip().splitlines()[-5:]
        out["arms"][arm] = {"commit": commit_id, "tree": tree, "uncommitted": int(dirty_count),
                            "files_added_or_changed": int(files), "python": python,
                            "content_sha256": tree_digest(target)}
        if arm == "N" and (commit_id != BASE_COMMIT or int(dirty_count)):
            raise SystemExit("N: the base copy is not a clean checkout of the base commit")
    runs = [suite_on_base(os.path.join(STATE, "arms", "baseline", str(i))) for i in (1, 2)]
    if any(code != 0 or cases is None for code, cases in runs):
        raise SystemExit(f"the existing suite does not pass on the base: exits {[code for code, _ in runs]}")
    if runs[0][1] != runs[1][1]:
        raise SystemExit("two runs of the existing suite on the base disagree; the baseline is not stable")
    if not runs[0][1] or any(status != "passed" for status in runs[0][1].values()):
        raise SystemExit("the existing suite on the base has cases that do not pass; the baseline must be all passed")
    with open(baseline_path(), "w", encoding="utf-8") as handle:
        json.dump({"exit": 0, "cases": runs[0][1]}, handle, indent=1, sort_keys=True)
        handle.write("\n")
    out["suite_baseline_sha256"], out["suite_cases"] = digest(baseline_path()), len(runs[0][1])
    out["suite_statuses"] = {s: sum(1 for v in runs[0][1].values() if v == s) for s in sorted(set(runs[0][1].values()))}
    json.dump(out, open(os.path.join(STATE, "arms", "arms.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


# ---------------------------------------------------------------- budget of the claude cell

def budget_path():
    return os.path.join(STATE, "budget.json")


def raise_path():
    return os.path.join(STATE, "budget-raise.jsonl")


def ledger_path():
    return os.path.join(STATE, "ledger-claude.jsonl")


def budget():
    """(cap, the owner decision behind it, logical tokens spent before this state folder): the base written once by
    `budget`, then every recorded raise in order. A raise must name an owner decision and raise the cap."""
    if not os.path.exists(budget_path()):
        raise SystemExit("no budget base in the state root; run `budget --spent-before N` first")
    base = json.load(open(budget_path(), encoding="utf-8"))
    cap, decision = int(base["cap"]), base["decision"]
    for entry in read_rows(raise_path()):
        if not re.fullmatch(r"D\d+", str(entry.get("decision"))) or int(entry.get("cap") or 0) <= cap:
            raise SystemExit("budget-raise.jsonl has an entry that names no decision or does not raise the cap")
        cap, decision = int(entry["cap"]), entry["decision"]
    return cap, decision, int(base["spent_before"])


def cmd_budget(args):
    """Write the budget base once, or record a raise that names the owner decision allowing it."""
    if args.raise_to is None:
        if os.path.exists(budget_path()):
            raise SystemExit("the budget base is written once")
        if args.spent_before is None or args.spent_before < 0:
            raise SystemExit("give --spent-before: logical tokens the claude cell used outside this state folder")
        with open(budget_path(), "w", encoding="utf-8") as handle:
            json.dump({"cap": CAP, "decision": CAP_DECISION, "spent_before": args.spent_before,
                       "written": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, handle, indent=1, sort_keys=True)
            handle.write("\n")
    else:
        if not re.fullmatch(r"D\d+", args.decision or ""):
            raise SystemExit("a raise names the owner decision that allows it (--decision D<number>)")
        if args.raise_to <= budget()[0]:
            raise SystemExit("a raise must be larger than the current cap")
        append(raise_path(), {"cap": args.raise_to, "decision": args.decision,
                              "written": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    cap, decision, before = budget()
    print(json.dumps({"cap": cap, "decision": decision, "spent_before": before, "spent": cell_spent()}, indent=1))
    return 0


def cell_spent():
    """Logical tokens of the claude cell: the spend before this state folder, every session that ended, and, for a
    session that started and never ended, the larger of its reserve and the usage left in its raw file."""
    before = budget()[2]
    started, ended = {}, {}
    for entry in read_rows(ledger_path()):
        (started if entry["event"] == "start" else ended)[entry["key"]] = entry
    total = before + sum(int(entry.get("tokens") or 0) for entry in ended.values())
    for key, entry in started.items():
        if key not in ended:
            raw = os.path.join(STATE, entry["raw"])
            seen = claude_usage(open(raw, encoding="utf-8", errors="replace"))[0] if os.path.exists(raw) else 0
            total += max(int(entry.get("reserve") or 0), seen)
    return total


def claude_lock():
    """One claude-cell process at a time per state folder; the lock is held until the process ends."""
    handle = open(os.path.join(STATE, "claude.lock"), "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit("another claude-cell run holds the lock of this state folder")
    return handle


# ---------------------------------------------------------------- one unit

def load_units(path):
    data = json.load(open(path, encoding="utf-8"))
    return data["klass"], data["units"], digest(path)


def run_unit(cell, arm, unit, klass, attempt, model, tag, budget_left=None, provenance=None):
    """All sessions of one unit in one arm, then the grade. Returns (row, reason it does not count or '').
    `budget_left` (claude cell): a function giving the logical tokens the cell may still spend. Each session is
    entered in the cell's ledger before it starts and after it ends; the session that passes the allowance is
    stopped, and a run after which the cell is over its cap does not count."""
    root = os.path.join(STATE, "runs", tag, cell, safe_id(unit), arm, f"a{attempt}")
    if os.path.isdir(root):
        root += f"-{int(time.time())}"
    append(starts_path(tag, cell), dict(provenance or {}, event="start", tag=tag, cell=cell, klass=klass, unit=unit["id"], arm=arm, attempt=attempt,
                                        root=os.path.relpath(root, STATE), time=time.strftime("%Y-%m-%dT%H:%M:%S%z")))
    work, raw = os.path.join(root, "work", "proj"), os.path.join(root, "raw")
    os.makedirs(os.path.dirname(work))
    os.makedirs(raw)
    shutil.copytree(arm_dir(arm), work, symlinks=True)
    row = {"cell": cell, "arm": arm, "unit": unit["id"], "klass": klass, "type": unit.get("type"), "attempt": attempt,
           "tag": tag, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "sessions": [], "flags": [],
           "arm_commit": arms_json()["arms"][arm[0]]["commit"], "carry": unit.get("carry", "home"),
           "root": os.path.relpath(root, STATE)}
    carry_home = row["carry"] == "home"
    reserve = estimate(klass, unit, arm) // max(1, len(unit["sessions"])) if cell == "claude" else 0
    home = None
    for index, text in enumerate(unit["sessions"]):
        name = f"s{index + 1}"
        if home is None or not carry_home:
            home = os.path.join(root, "home" if carry_home else f"home-{name}")
            os.makedirs(home)
        prompt = text if unit.get("verbatim") else PROMPT.format(task=text)
        if cell == "claude":
            left = budget_left()
            if left <= 0:
                row["not_run"] = f"{name}: budget cap"
                break
            key = os.path.relpath(os.path.join(raw, f"{name}.jsonl"), STATE)
            append(ledger_path(), {"event": "start", "key": key, "raw": key, "reserve": reserve,
                                   "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
            session = run_claude(work, home, prompt, SESSION_SECONDS, model, raw, name, left)
            append(ledger_path(), {"event": "end", "key": key, "tokens": session.get("tokens_total") or 0,
                                   "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
        else:
            session = run_codex(work, home, prompt, SESSION_SECONDS, model, raw, name)
        with open(os.path.join(raw, f"{name}.final.txt"), "w", encoding="utf-8") as handle:
            handle.write(session.pop("final") + "\n---\n" + session.pop("stderr_tail", ""))
        session["memory_files"] = memory_files(home)
        session["changed"] = changed_paths(work)
        if unit.get("facts"):
            session["fact_places"] = fact_places(work, home, unit["facts"])
        row["sessions"].append(session)
        reason = not_run(session, cell, model)
        if not reason and cell == "claude" and budget_left() < 0:
            reason = "budget cap"
        if reason:
            row["not_run"] = f"{name}: {reason}"
            break
        if session["exit"] in ("timeout", "token ceiling"):
            row["flags"].append(f"{name} {session['exit']}")  # an answer; the later sessions are still sent
        if session.get("over_ceiling"):
            row["flags"].append(f"{name} over the token ceiling with its subagents")  # an answer, flagged
    row["tokens_total"] = sum(s.get("tokens_total") or 0 for s in row["sessions"])
    row["tokens_noncache"] = sum(s.get("tokens_noncache") or 0 for s in row["sessions"])
    row["seconds"] = round(sum(s["seconds"] for s in row["sessions"]), 1)
    row["top_level_added"] = sorted(set(os.listdir(work)) - set(os.listdir(arm_dir("N"))))[:50]
    if not row.get("not_run"):
        for _try in range(2):  # grading is mechanical; a second try only covers a failure of the grading step itself
            row["grade"] = grade(unit, work, os.path.join(root, "grade"), ref=row["arm_commit"])
            if not row["grade"]["error"]:
                break
        row["score"] = row["grade"]["score"]
        if row["grade"]["error"] or row["score"] is None:
            row["not_run"] = f"grading failed: {row['grade']['error'] or 'no test function was collected'}"
    row["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    return row, row.get("not_run", "")


def starts_path(tag, cell):
    return os.path.join(STATE, f"starts-{tag}-{cell}.jsonl")


def tried(tag, cell, unit_id, arm=None):
    """Every attempt of a unit (in one arm) under a tag: the finished ones from the attempts file, and, for a run
    that was started and never finished (the runner was stopped or killed), a failed attempt 'interrupted'. So an
    attempt cannot be dropped by stopping the runner."""
    finished = [r for r in read_rows(os.path.join(STATE, f"attempts-{tag}-{cell}.jsonl"))
                if r["unit"] == unit_id and arm in (None, r["arm"])]
    roots = {r.get("root") for r in finished}
    lost = [dict(s, not_run="interrupted") for s in read_rows(starts_path(tag, cell))
            if s["unit"] == unit_id and arm in (None, s["arm"]) and s["root"] not in roots]
    return finished + lost


class rows_lock:
    """Writing an attempt and its row, and recovering rows, is done by one process at a time per tag and cell."""

    def __init__(self, tag, cell):
        self.path = os.path.join(STATE, f"rows-{tag}-{cell}.lock")

    def __enter__(self):
        self.handle = open(self.path, "w")
        fcntl.flock(self.handle, fcntl.LOCK_EX)
        return self

    def __exit__(self, *_exc):
        self.handle.close()


def recover(tag, cell):
    """Rows are written after attempts. If the runner stopped in between, the counted attempt is written to the rows
    now, so that a finished run is never run again."""
    rows_path = os.path.join(STATE, f"rows-{tag}-{cell}.jsonl")
    with rows_lock(tag, cell):
        kept = {r.get("root") for r in read_rows(rows_path)}
        for attempt in read_rows(os.path.join(STATE, f"attempts-{tag}-{cell}.jsonl")):
            if not attempt.get("not_run") and attempt.get("root") not in kept:
                append(rows_path, attempt)
                print(f"recovered the counted attempt {attempt['root']}", flush=True)


def main_started():
    """Whether any main run has started: from then on the unit files and FREEZE.json are fixed."""
    return any(read_rows(path) for pattern in ("starts-main-*.jsonl", "attempts-main-*.jsonl", "rows-main-*.jsonl")
               for path in glob.glob(os.path.join(STATE, pattern)))


def append(path, row):
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_rows(path):
    if not path or not os.path.exists(path):
        return []
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def schedule(cell, klass, units, arms):
    """(unit, arm) in running order: units in file order, arms rotated by the unit's place among the twelve."""
    unknown = [a for a in arms if a not in ARMS[cell][klass]]
    if unknown:
        raise SystemExit(f"{cell} class {klass} has no arm {unknown}")
    order = [a for a in ARMS[cell][klass] if a in arms]
    plan = []
    for place, unit in enumerate(units):
        shift = (OFFSET[klass] + place) % len(order)
        plan += [(unit, arm) for arm in order[shift:] + order[:shift]]
    return plan


def estimate(klass, unit, arm):
    """Logical tokens the next claude run is expected to cost: the largest counted main run of the same class and
    arm so far, the first estimate otherwise."""
    seen = [r["tokens_total"] for r in read_rows(os.path.join(STATE, "rows-main-claude.jsonl"))
            if r["klass"] == klass and r["arm"][0] == arm[0]]
    return max(seen) if seen else ESTIMATE[klass][arm[0]] * len(unit["sessions"])


def gate():
    """Whether the claude cell may start class C: its own class A and B runs scaled by what the same runs cost in
    the codex cell give a projection for class C, which must fit under the cap with a reserve. The first decision
    made with complete inputs is stored: an open gate stays open on resume (the cap still governs every run); a
    closed one is decided again only after a raise of the cap has been recorded."""
    def key(row):
        return row["unit"], row["arm"]

    path = os.path.join(STATE, "gate-C.json")
    cap, decision, _before = budget()
    raises = len(read_rows(raise_path()))
    if os.path.exists(path):
        stored = json.load(open(path, encoding="utf-8"))
        if stored["open"] or stored["raises"] == raises:
            return dict(stored, stored=True)
    claude = read_rows(os.path.join(STATE, "rows-main-claude.jsonl"))
    codex = read_rows(os.path.join(STATE, "rows-main-codex.jsonl"))
    mine = {key(r): r["tokens_total"] for r in claude if r["klass"] in ("A", "B") and r["arm"] in PRIMARY}
    theirs = {key(r): r["tokens_total"] for r in codex if r["klass"] in ("A", "B") and r["arm"] in PRIMARY}
    class_c = [r["tokens_total"] for r in codex if r["klass"] == "C" and r["arm"] in PRIMARY]
    out = {"cap": cap, "decision": decision, "raises": raises, "spent": cell_spent(), "claude_ab_runs": len(mine),
           "codex_same_runs": len(set(mine) & set(theirs)), "codex_c_runs": len(class_c)}
    if len(mine) != 24 or set(mine) - set(theirs) or len(class_c) != 12:
        return dict(out, open=False, stored=False, reason="needs the claude cell's 24 class A and B runs, the same "
                                                          "runs in the codex cell and the codex cell's 12 class C runs")
    ratio = sum(mine.values()) / sum(theirs[k] for k in mine)
    projected = ratio * sum(class_c)
    needed = out["spent"] + RESERVE * projected
    out = dict(out, ratio=round(ratio, 4), projected=round(projected), needed=round(needed), open=needed <= cap,
               reason="" if needed <= cap else "the projection with its reserve does not fit under the cap",
               decided=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=1, sort_keys=True)
    return dict(out, stored=False)


def cmd_gate(_args):
    state = gate()
    print(json.dumps(state, indent=1))
    return 0 if state["open"] else 4


def cmd_run(args):
    """Run units. Tag main: the frozen units of --klass with the frozen arms and model, after the state is checked
    against FREEZE.json. Tag calibration: the class C calibration units in the codex cell, arm N1. Every row is
    bound to the digest of the unit entry it ran, the unit file and this runner; results of another runner, or of
    another version of a unit, are refused rather than reused."""
    main_run, calibration = args.tag == "main", args.tag == "calibration"
    if (main_run or calibration) and (args.only or args.arms or args.model or args.units):
        raise SystemExit(f"tag {args.tag} runs fixed units, arms and model; --only, --arms, --model and --units are "
                         "for other tags")
    freeze_digest = ""
    if main_run:
        if not args.klass:
            raise SystemExit("tag main needs --klass")
        args.freeze = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FREEZE.json")
        frozen, now = json.load(open(args.freeze, encoding="utf-8")), manifest()
        differ = sorted(k for k in set(frozen) | set(now) if frozen.get(k) != now.get(k))
        if differ:
            print(f"the state differs from {os.path.basename(args.freeze)} in: {', '.join(differ)}", flush=True)
            return 6
        freeze_digest = digest(args.freeze)
    if calibration:
        if args.cell != "codex" or args.klass not in (None, "C"):
            raise SystemExit("tag calibration runs class C in the codex cell")
        path = os.path.join(STATE, "units_C_calibration.json")
    else:
        path = args.units or (os.path.join(STATE, f"units_{args.klass}.json") if args.klass else "")
    if not path:
        raise SystemExit("give --klass or --units")
    klass, units, units_digest = load_units(path)
    if args.klass and klass != args.klass:
        raise SystemExit(f"{os.path.basename(path)} holds class {klass}")
    if args.only:
        units = [u for u in units if u["id"] in args.only.split(",")]
    arms = ["N1"] if calibration else args.arms.split(",") if args.arms else ARMS[args.cell][klass]
    model = args.model or MODELS[args.cell]
    rows_path = os.path.join(STATE, f"rows-{args.tag}-{args.cell}.jsonl")
    attempts_path = os.path.join(STATE, f"attempts-{args.tag}-{args.cell}.jsonl")
    runner = digest(os.path.abspath(__file__))
    earlier_runs = read_rows(rows_path) + read_rows(attempts_path) + read_rows(starts_path(args.tag, args.cell))
    if any(not known_runner(r.get("runner_sha256"), main=main_run) for r in earlier_runs):
        raise SystemExit(f"runs of another runner version exist under tag {args.tag}; use a new state folder")
    entries = {u["id"]: unit_digest(u) for u in units}
    for r in earlier_runs:
        if r["unit"] in entries and (r.get("unit_sha256") != entries[r["unit"]]
                                     or (main_run and r.get("freeze_sha256") != freeze_digest)):
            raise SystemExit(f"{r['unit']}: a run exists for another version of this unit or another FREEZE.json")
    recover(args.tag, args.cell)
    lock = claude_lock() if args.cell == "claude" else None
    cap = decision = None
    if args.cell == "claude":
        cap, decision, _before = budget()
    if main_run and args.cell == "claude" and klass == "C":
        state = gate()
        print("class C gate: " + json.dumps(state), flush=True)
        if not state["open"]:
            return 4
    done = {(r["unit"], r["arm"]) for r in read_rows(rows_path)}
    for unit, arm in schedule(args.cell, klass, units, arms):
        while (unit["id"], arm) not in done:
            earlier = tried(args.tag, args.cell, unit["id"], arm)
            failed = [r for r in earlier if r.get("not_run")
                      and not any(word in r["not_run"] for word in ("usage limit", "budget cap"))]
            if len(failed) >= MAX_ATTEMPTS:
                print(f"{unit['id']}/{arm}: {len(failed)} attempts did not count; stopping", flush=True)
                return 5
            budget_left = None
            if args.cell == "claude":
                cap, decision, _before = budget()
                spent, need = cell_spent(), estimate(klass, unit, arm)
                if spent + need > cap:
                    print(f"budget: spent {spent:,}; the next run (about {need:,}) does not fit under {cap:,}",
                          flush=True)
                    return 4

                def budget_left():
                    return budget()[0] - cell_spent()

            provenance = {"units_sha256": units_digest, "unit_sha256": entries[unit["id"]],
                          "candidate_sha256": unit.get("candidate_sha256"), "runner_sha256": runner,
                          "freeze_sha256": freeze_digest}
            row, reason = run_unit(args.cell, arm, unit, klass, len(earlier) + 1, model, args.tag, budget_left,
                                   provenance)
            row.update(provenance, model_asked=model, cap=cap, cap_decision=decision)
            with rows_lock(args.tag, args.cell):
                append(attempts_path, row)
                if not reason:
                    append(rows_path, row)
            print(f"{args.cell} {unit['id']}/{arm} a{row['attempt']}: " + (f"NOT RUN ({reason}), " if reason else
                  f"score {row['score']} ({row['grade']['passed']}/{row['grade']['n']}"
                  f"{', suite regression' if row['grade']['suite_regression'] else ''}), ")
                  + f"{row['tokens_total']:,} tokens, {row['seconds']:.0f}s {row['flags'] or ''}", flush=True)
            if not reason:
                done.add((unit["id"], arm))
            elif "usage limit" in reason:
                return 3
            elif "budget cap" in reason:
                return 4
    del lock
    return 0


# ---------------------------------------------------------------- unit verification (no model)

HUNK = re.compile(r"@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")


def patch_walk(patch):
    """(kind, line) for every line of a unified diff; kind is head, add, del, ctx or note. Hunk bodies are followed
    by their line counts, so a content line that looks like a file header is not taken for one."""
    old = new = 0
    for line in patch.splitlines():
        if old > 0 or new > 0:
            if line.startswith("\\"):
                yield "note", line
            elif line.startswith("+"):
                new -= 1
                yield "add", line
            elif line.startswith("-"):
                old -= 1
                yield "del", line
            else:
                old, new = old - 1, new - 1
                yield "ctx", line
            continue
        match = HUNK.match(line)
        if match:
            old = 1 if match.group(1) is None else int(match.group(1))
            new = 1 if match.group(2) is None else int(match.group(2))
        yield ("note" if line.startswith("\\") else "head"), line


def patch_files(patch):
    """The paths a diff touches, the text of its added lines, and per file its added and deleted lines and whether
    the diff creates the file. The current file is set by each `diff --git` line and refined by `---` and `+++`."""
    paths, added, files, current, created = set(), [], {}, None, False

    def entry(name):
        return files.setdefault(name, {"added": 0, "deleted": 0, "new": False})

    def plain(name):
        name = name[4:].split("\t")[0].strip()
        return name if name == "/dev/null" else name[2:] if name.startswith(("a/", "b/")) else name

    for kind, line in patch_walk(patch):
        if kind == "head" and line.startswith("diff --git "):
            match = re.match(r"diff --git a/(.+?) b/(.+)$", line)
            names = list(match.groups()) if match else ["<unreadable>"]
            paths.update(names)
            current, created = names[-1], False
            entry(current)
        elif kind == "head" and line.startswith("new file mode") and current:
            entry(current)["new"] = True
        elif kind == "head" and line.startswith("--- "):
            name = plain(line)
            created = name == "/dev/null"
            if not created:
                paths.add(name)
                current = name
        elif kind == "head" and line.startswith("+++ "):
            name = plain(line)
            if name != "/dev/null":
                paths.add(name)
                current = name
                entry(current)["new"] = entry(current)["new"] or created
        elif kind == "head" and line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
            paths.add(line.split(" ", 2)[2].strip())
        elif kind == "add":
            added.append(line[1:])
            if current:
                entry(current)["added"] += 1
        elif kind == "del" and current:
            entry(current)["deleted"] += 1
    return sorted(paths), added, files


OAW_MODE = []


def oaw_mode():
    """The harness's own oaw_mode.py at the commit under test, loaded once without writing a cache."""
    if not OAW_MODE:
        spec = importlib.util.spec_from_file_location("h1_frozen_oaw_mode", os.path.join(OAW, "scripts", "oaw_mode.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        OAW_MODE.append(module)
    return OAW_MODE[0]


def code_lines(files):
    """Added plus deleted lines of the files that the frozen oaw_mode.py does not count as documentation; the same
    count it compares with STANDARD_LINES when it decides that a change is large."""
    mode = oaw_mode()
    return sum(f["added"] + f["deleted"] for path, f in files.items() if not mode.is_doc(path))


def token_in(fact, text):
    return bool(re.search(EDGE % re.escape(str(fact)), text))


def swap_added(patch, mapping):
    """The diff with every whole-token occurrence of a key replaced by its value, in added lines only."""
    pattern = re.compile("|".join(EDGE % re.escape(key) for key in sorted(mapping, key=len, reverse=True)))
    lines = [("+" + pattern.sub(lambda match: mapping[match.group(0)], line[1:])) if kind == "add" else line
             for kind, line in patch_walk(patch)]
    return "\n".join(lines) + "\n"


def wrong_value(fact):
    return fact + ("9" if fact[-1:].isdigit() else "_X")


REPO = []


def repo_has(fact):
    """Whether the fact stands as a whole token anywhere in the corpus at the base commit (venv and git left out)."""
    if not REPO:
        template = arm_dir("N")
        for base, dirs, names in os.walk(template):
            dirs[:] = [d for d in dirs if not (base == template and d in (".venv", ".git"))]
            for name in names:
                path = os.path.join(base, name)
                if os.path.isfile(path) and not os.path.islink(path):
                    REPO.append(open(path, "rb").read())
    pattern = re.compile((EDGE % re.escape(str(fact))).encode())
    return any(pattern.search(data) for data in REPO)


def verify_unit(unit, klass, root):
    checks, mutants = {}, {}
    sessions, patch, kind = unit.get("sessions") or [], unit.get("reference_patch") or "", unit.get("type")
    paths, added, files = patch_files(patch)
    lines = code_lines(files)
    note = [design_note(unit)] if design_note(unit) else (
        sorted(set(re.findall(r"docs/designs/[\w.-]+\.md", sessions[0]))) if kind == "design" and sessions else [])
    checks["patch_paths_allowed"] = bool(paths) and all(
        p.startswith("src/") or (len(note) == 1 and p == note[0]) for p in paths)
    where = os.path.join(root, safe_id(unit))
    at_base = grade(unit, arm_dir("N"), os.path.join(where, "base"), suite=False)
    checks["hidden_fails_at_base"] = at_base["hidden_exit"] not in (0, None)
    with_ref = grade(unit, arm_dir("N"), os.path.join(where, "ref"), patch=patch)
    checks["patch_applies"] = with_ref["script_exit"] == 0
    functions = sorted(with_ref["collected"])
    nodes = {fn: with_ref["nodes"][fn] for fn in functions}
    items = {fn: [fn] for fn in functions}
    checks["plain_functions"] = checks["patch_applies"] and not with_ref["alien"]
    checks["hidden_passes_with_reference"] = with_ref["hidden_exit"] == 0 and bool(functions) \
        and all(with_ref["functions"].get(fn) for fn in functions)
    checks["suite_passes_with_reference"] = with_ref["suite_exit"] == 0 and with_ref["suite_regression"] is False

    def mutant(name, mapping):
        """Grade the reference with some of its values replaced; the functions that still pass, or None."""
        frozen = dict(unit, functions=functions, nodes=nodes, items=items)
        result = grade(frozen, arm_dir("N"), os.path.join(where, name), patch=swap_added(patch, mapping), suite=False)
        mutants[name] = result["functions"] if result["script_exit"] == 0 else None
        return mutants[name]

    def breaks_recall(result, recall):
        return result is not None and bool(recall) and any(not result.get(fn) for fn in recall)

    if klass == "B":
        facts = [str(f) for f in unit.get("facts") or []]
        old = [str(f) for f in unit.get("superseded_facts") or []]
        recall = [fn for fn in functions if fn.startswith("test_recall_")]
        base_of = {fn: int(fn[11]) for fn in functions if re.fullmatch(r"test_base_s[1-9]_\w+", fn)}
        checks["session_count"] = len(sessions) == (3 if kind == "superseded" else 2)
        checks["function_names"] = all(re.fullmatch(r"test_recall_\w+", fn) or base_of.get(fn, 99) <= len(sessions)
                                       for fn in functions)
        checks["function_count"] = 4 <= len(functions) <= 8 and len(recall) >= 2
        checks["base_test_per_earlier_session"] = len(sessions) > 1 and all(
            number in base_of.values() for number in range(1, len(sessions)))
        checks["recall_fails_at_base"] = not any(at_base["functions"].get(fn) for fn in recall)
        checks["facts_listed"] = len(facts) >= 2 and len(set(facts)) == len(facts) and all(f.strip() for f in facts)
        values = facts + old
        checks["facts_independent"] = not any(a != b and a in b for a in values for b in values)
        checks["facts_not_in_final_prompt"] = bool(sessions) and not any(f in sessions[-1] for f in values if f)
        earlier = sessions[1:2] if kind == "superseded" else sessions[:-1]
        checks["facts_stated_earlier"] = bool(facts) and all(any(f in s for s in earlier) for f in facts)
        checks["facts_not_in_repo"] = not any(repo_has(f) for f in facts if f)
        checks["facts_in_reference_patch"] = bool(facts) and all(any(token_in(f, line) for line in added) for f in facts)
        ready = checks["patch_applies"] and checks["facts_listed"] and checks["facts_in_reference_patch"] \
            and checks["facts_independent"]
        wrong = mutant("wrong", {f: wrong_value(f) for f in facts}) if ready else None
        checks["wrong_values_fail_every_recall_test"] = wrong is not None and bool(recall) \
            and not any(wrong.get(fn) for fn in recall)
        checks["wrong_values_pass_every_base_test"] = wrong is not None and all(wrong.get(fn) for fn in base_of)
        # Each fact alone: an answer that gets only this one fact wrong must fail a recall test and nothing else.
        alone = [mutant(f"wrong-{i + 1}", {f: wrong_value(f)}) if ready else None for i, f in enumerate(facts)]
        checks["each_wrong_value_fails_a_recall_test"] = bool(alone) and all(breaks_recall(m, recall) for m in alone)
        checks["each_wrong_value_passes_every_base_test"] = bool(alone) and all(
            m is not None and all(m.get(fn) for fn in base_of) for m in alone)
        if kind == "superseded":
            checks["superseded_facts_listed"] = len(old) == len(facts) and all(
                o.strip() and o != f for o, f in zip(old, facts))
            checks["superseded_facts_stated_first"] = bool(old) and bool(sessions) and all(o in sessions[0] for o in old)
            usable = ready and checks["superseded_facts_listed"]
            stale = mutant("old", dict(zip(facts, old))) if usable else None
            checks["old_values_fail_every_recall_test"] = stale is not None and bool(recall) \
                and not any(stale.get(fn) for fn in recall)
            checks["old_values_pass_every_base_test"] = stale is not None and all(stale.get(fn) for fn in base_of)
            back = [mutant(f"old-{i + 1}", {f: o}) if usable else None for i, (f, o) in enumerate(zip(facts, old))]
            checks["each_old_value_fails_a_recall_test"] = bool(back) and all(breaks_recall(m, recall) for m in back)
            checks["each_old_value_passes_every_base_test"] = bool(back) and all(
                m is not None and all(m.get(fn) for fn in base_of) for m in back)
    if klass == "C":
        requirements = unit.get("requirements") or {}
        if not isinstance(requirements, dict):
            requirements = {}

        def flat(text):
            return " ".join(str(text).split())

        items = {key: [fn for fn in functions if fn[5:8] == key] for key in sorted(requirements)}
        checks["session_count"] = len(sessions) == 1
        checks["function_names"] = all(re.fullmatch(r"test_r\d\d_\w+", fn) for fn in functions)
        checks["function_count"] = 1 <= len(functions) <= 20
        checks["requirement_count"] = 8 <= len(requirements) <= 12 and all(
            re.fullmatch(r"r\d\d", key) for key in requirements)
        checks["requirements_in_prompt"] = bool(requirements) and bool(sessions) and all(
            flat(text) and flat(text) in flat(sessions[0]) for text in requirements.values())
        checks["every_requirement_tested"] = bool(items) and all(items.values())
        checks["every_function_listed"] = all(fn[5:8] in requirements for fn in functions)
        if kind == "large":
            checks["large_enough"] = lines >= oaw_mode().STANDARD_LINES
        if kind == "design":
            checks["design_note_named"] = len(note) == 1
            made = files.get(note[0]) if len(note) == 1 else None
            checks["design_note_added"] = bool(made) and made["new"] and made["added"] > 0
    return {"id": unit["id"], "type": kind, "valid": all(checks.values()), "checks": checks, "functions": functions,
            "nodes": nodes, "items": items, "mutants": mutants, "reference_lines": lines,
            "suite_tail": with_ref["suite_tail"], "hidden_tail": with_ref["hidden_tail"], "sha256": unit_digest(unit)}


def candidate_units(path):
    """The units of a candidates file (class A's source calls them tasks and gives one prompt each)."""
    data = json.load(open(path, encoding="utf-8"))
    units = (data.get("units") or data.get("tasks") or []) if isinstance(data, dict) else []
    for unit in units:
        unit.setdefault("sessions", [unit["prompt"]] if unit.get("prompt") else [])
    return units


# ---------------------------------------------------------------- the author ledger

def runner_digest():
    return digest(os.path.abspath(__file__))


def known_runner(value, main=False):
    """This runner, or for records made before the freeze an earlier version listed in PRIOR_RUNNERS."""
    return value == runner_digest() or (not main and value in PRIOR_RUNNERS)


def authors_path():
    return os.path.join(STATE, "authors.jsonl")


def brief_path(klass):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), f"AUTHOR_BRIEF_{klass}.md")


def candidates_path(name, klass):
    return os.path.join(STATE, f"candidates-{name}-units_{klass}.json")


def verified_path(name, klass):
    return os.path.join(STATE, f"verified-{name}-{klass}.json")


def missing_path(klass):
    return os.path.join(STATE, f"missing-{klass}.json")


def counted_authors(klass):
    """The author runs of a class that count, in authoring order: (name, start entry, end entry or None). A run that
    started and never ended counts; one that ended as not run does not."""
    starts, ends = [], {}
    for entry in read_rows(authors_path()):
        if entry.get("klass") == klass:
            if entry["event"] == "start":
                starts.append(entry)
            else:
                ends[entry["name"]] = entry
    return [(s["name"], s, ends.get(s["name"])) for s in starts if not (ends.get(s["name"]) or {}).get("not_run")]


def author_record(klass, name):
    """The counted run of this author, with its candidates file checked against the digest the ledger holds."""
    for found, start, end in counted_authors(klass):
        if found == name:
            entry = ((end or {}).get("files") or {}).get(f"units_{klass}.json") or {}
            path = candidates_path(name, klass)
            if not entry.get("sha256") or not os.path.exists(path):
                raise SystemExit(f"author {name} left no usable units_{klass}.json")
            if digest(path) != entry["sha256"]:
                raise SystemExit(f"the candidates of author {name} changed after the author run")
            return start, end
    raise SystemExit(f"no counted class {klass} author called {name}")


def author_units(klass, name):
    """The candidate units of a counted author; a supplement contributes only units of the types it supplies."""
    start, _end = author_record(klass, name)
    units = candidate_units(candidates_path(name, klass))
    return [u for u in units if u.get("type") in start["supplies"]] if start.get("supplies") else units


def checked(candidates, verified):
    """The verification report of a candidates file, refused when it was made from another file, by another runner,
    on another suite baseline or with another oaw_mode.py."""
    report = json.load(open(verified, encoding="utf-8"))
    now = {"candidates_sha256": digest(candidates), "baseline_sha256": digest(baseline_path()),
           "oaw_mode_sha256": digest(os.path.join(OAW, "scripts", "oaw_mode.py"))}
    differ = [key for key, value in now.items() if report.get(key) != value]
    if not known_runner(report.get("runner_sha256")):
        differ.append("runner_sha256")
    if differ:
        raise SystemExit(f"{os.path.basename(verified)} does not match the current {', '.join(differ)}")
    return report


def cmd_author(args):
    """One zero-context session writes candidate units from the class's brief, in a copy of the plain corpus. The
    ledger gets a start entry before and an end entry after it. The first author of a class may run at any time; a
    supplement only after `freeze` has recorded which types are missing, at most MAX_AUTHORS counted runs in all.
    Only _out/units_<class>.json is taken, with the author's name added to every unit id."""
    klass = args.klass
    if not re.fullmatch(r"[a-z0-9]+", args.name):
        raise SystemExit("the author name is lower-case letters and digits only")
    root = os.path.join(STATE, "authors", args.name)
    if os.path.isdir(root) or any(entry.get("name") == args.name for entry in read_rows(authors_path())):
        raise SystemExit(f"author {args.name} already ran; use a new name")
    counted, supplies = counted_authors(klass), None
    if counted:
        if len(counted) >= MAX_AUTHORS:
            raise SystemExit(f"class {klass} already has {len(counted)} counted author runs; stop and report to the owner")
        if not os.path.exists(missing_path(klass)):
            raise SystemExit(f"a supplement needs `freeze --klass {klass}` to have recorded the missing types first")
        missing = json.load(open(missing_path(klass), encoding="utf-8"))
        if missing["after_authors"] != [name for name, _start, _end in counted]:
            raise SystemExit(f"missing-{klass}.json was not written after the last counted author; run freeze again")
        supplies = missing["types"]
    brief = brief_path(klass)
    append(authors_path(), {"event": "start", "klass": klass, "name": args.name, "brief_sha256": digest(brief),
                            "runner_sha256": runner_digest(), "supplies": supplies,
                            "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    work, home, raw = os.path.join(root, "work", "proj"), os.path.join(root, "home"), os.path.join(root, "raw")
    os.makedirs(os.path.dirname(work))
    os.makedirs(home)
    os.makedirs(raw)
    shutil.copytree(arm_dir("N"), work, symlinks=True)
    session = run_codex(work, home, open(brief, encoding="utf-8").read(), args.hours * 3600, MODELS["codex"], raw,
                        "author")
    final = session.pop("final")
    with open(os.path.join(raw, "author.final.txt"), "w", encoding="utf-8") as handle:
        handle.write(final)
    reason = not_run(session, "codex", MODELS["codex"])
    files, name = {}, f"units_{klass}.json"
    source = os.path.join(work, "_out", name)
    if os.path.isfile(source) and not os.path.islink(source):
        shutil.copyfile(source, os.path.join(raw, name))
        files[name] = {"raw_sha256": digest(source)}
        try:
            data = json.load(open(source, encoding="utf-8"))
            for unit in data["units"]:
                unit["id"] = f"{unit['id']}-{args.name}"
                safe_id(unit)
            with open(candidates_path(args.name, klass), "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=1, ensure_ascii=False)
            files[name].update({"sha256": digest(candidates_path(args.name, klass)),
                                "units": [unit["id"] for unit in data["units"]]})
        except (ValueError, KeyError, TypeError, SystemExit) as error:
            files[name]["error"] = str(error)[:200]
    summary = {"event": "end", "klass": klass, "name": args.name, "exit": session["exit"], "not_run": reason,
               "tokens_total": session["tokens_total"], "tokens_noncache": session["tokens_noncache"],
               "seconds": session["seconds"], "model": session.get("model"), "final": final[:300], "files": files,
               "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    append(authors_path(), summary)
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    return 0 if (files.get(name) or {}).get("sha256") and not reason else 5


def cmd_verify(args):
    """Mechanical checks of every candidate unit. Class A: --candidates and --out. Classes B and C: --author, whose
    candidates and report have fixed places in the state root."""
    if args.klass == "A":
        if not (args.candidates and args.out) or args.author:
            raise SystemExit("class A: give --candidates and --out")
        candidates, out, units = args.candidates, args.out, candidate_units(args.candidates)
    else:
        if not args.author or args.candidates or args.out:
            raise SystemExit("classes B and C: give --author only")
        candidates, out = candidates_path(args.author, args.klass), verified_path(args.author, args.klass)
        units = author_units(args.klass, args.author)
    report = []
    for unit in units:
        result = verify_unit(unit, args.klass, os.path.join(STATE, "verify", args.klass))
        report.append(result)
        failed = [name for name, good in result["checks"].items() if not good]
        print(unit["id"], "VALID" if result["valid"] else f"DROP {failed}", len(result["functions"]), "functions,",
              result["reference_lines"], "lines", flush=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"klass": args.klass, "author": args.author, "candidates_sha256": digest(candidates),
                   "runner_sha256": runner_digest(), "baseline_sha256": digest(baseline_path()),
                   "oaw_mode_sha256": digest(os.path.join(OAW, "scripts", "oaw_mode.py")), "units": report},
                  handle, indent=1, ensure_ascii=False)
    return 0


# ---------------------------------------------------------------- unit checks by a zero-context session

def bound_to(report, verified):
    """The digests a solver row or an audit entry carries, so that it can only stand for this version of the unit,
    this verification report and this runner."""
    return {"candidate_sha256": report["sha256"], "verified_sha256": digest(verified), "runner_sha256": runner_digest()}


def refuse_other(found, bound, what):
    differ = [key for key, value in bound.items()
              if not (known_runner(found.get(key)) if key == "runner_sha256" else found.get(key) == value)]
    if differ:
        raise SystemExit(f"{what} exists for another {', '.join(differ)}; use a new state folder")


def cmd_solver(args):
    """Class B: one session that is given every request of the unit at once (perfect memory) must pass the hidden
    test. A unit it cannot pass is under-specified and is dropped."""
    author_record("B", args.author)
    candidates, verified_file = candidates_path(args.author, "B"), verified_path(args.author, "B")
    verified = {u["id"]: u for u in checked(candidates, verified_file)["units"]}
    rows_path = os.path.join(STATE, "rows-solver-codex.jsonl")
    attempts_path = os.path.join(STATE, "attempts-solver-codex.jsonl")
    recover("solver", "codex")
    for unit in author_units("B", args.author):
        report = verified.get(unit["id"]) or {}
        if not report.get("valid"):
            continue
        if unit_digest(unit) != report["sha256"]:
            raise SystemExit(f"{unit['id']} is not the unit that was verified")
        bound = bound_to(report, verified_file)
        prior = [r for r in read_rows(rows_path) if r["unit"] == unit["id"]]
        earlier = tried("solver", "codex", unit["id"])
        for found in prior + earlier:
            refuse_other(found, bound, f"a solver result of {unit['id']}")
        if prior:
            continue
        if sum(1 for r in earlier if r.get("not_run") and "usage limit" not in r["not_run"]) >= MAX_ATTEMPTS:
            print(unit["id"], f"{len(earlier)} attempts did not count; stopping", flush=True)
            return 5
        requests = "\n\n".join(f"Request {i + 1}:\n{text}" for i, text in enumerate(unit["sessions"]))
        single = dict(unit, sessions=[SOLVER_PROMPT.format(requests=requests)], verbatim=True, carry="home",
                      functions=report["functions"], nodes=report["nodes"], items=report["items"])
        row, reason = run_unit("codex", "N1", single, "B", len(earlier) + 1, MODELS["codex"], "solver",
                               provenance=bound)
        row.update(bound)
        with rows_lock("solver", "codex"):
            append(attempts_path, row)
            if not reason:
                append(rows_path, row)
        print(unit["id"], f"NOT RUN ({reason})" if reason else f"score {row['score']}", f"{row['tokens_total']:,}",
              flush=True)
        if reason:
            return 3 if "usage limit" in reason else 5
    return 0


AUDIT_PROMPT = """The repository in the current directory is pallets/flask. Do not change any file.

Below are a task description that was given to an engineer and a pytest file that is used afterwards to check the
result. For every test function, decide whether what it checks was stated in the task description. A function
counts as stated only when every name, signature, config key, default value, message text and behaviour that it
relies on is given in the description, or is already true of this repository before the task. A function that needs
a choice the description leaves open (a name, a wording, an order, an edge case it does not mention) is not stated.

Reply with JSON only, no other text:
{"functions": [{"name": "<test function>", "stated": true or false, "sentence": "<the sentence of the description it checks, or empty>", "reason": "<one short sentence>"}]}

## Task description
<<<
%s
>>>

## Test file
<<<
%s
>>>
"""


def audit_answer(text, functions):
    """The audit reply checked against a strict schema: one JSON object whose `functions` list holds exactly one
    object per frozen test function, each with a string `name` and a boolean `stated`. (reply, '') or (None, why)."""
    match = re.search(r"\{.*\}", text, re.S)
    try:
        reply = json.loads(match.group(0)) if match else None
    except ValueError:
        return None, "not JSON"
    if not isinstance(reply, dict) or not isinstance(reply.get("functions"), list):
        return None, "no functions list"
    names = []
    for entry in reply["functions"]:
        if not (isinstance(entry, dict) and isinstance(entry.get("name"), str) and isinstance(entry.get("stated"), bool)):
            return None, "an entry breaks the schema"
        names.append(entry["name"])
    if len(names) != len(set(names)):
        return None, "a function is listed twice"
    if set(names) != set(functions):
        return None, "the functions differ from the frozen ones"
    return reply, ""


def cmd_audit(args):
    """Class C: a zero-context read-only session says, per hidden test function, whether the prompt states what the
    function checks. A unit with a function it marks as not stated is dropped when the units are frozen. A reply that
    breaks the schema is recorded and the command stops; after MAX_ATTEMPTS such replies the unit is invalid."""
    author_record("C", args.author)
    candidates, verified_file = candidates_path(args.author, "C"), verified_path(args.author, "C")
    verified = {u["id"]: u for u in checked(candidates, verified_file)["units"]}
    out_path = os.path.join(STATE, "audit-C.json")
    audit = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    for unit in author_units("C", args.author):
        report = verified.get(unit["id"]) or {}
        if not report.get("valid"):
            continue
        if unit_digest(unit) != report["sha256"]:
            raise SystemExit(f"{unit['id']} is not the unit that was verified")
        bound = bound_to(report, verified_file)
        entry = audit.get(unit["id"])
        if entry:
            refuse_other(entry, bound, f"an audit of {unit['id']}")
            if entry["result"] is not None or entry["invalid"]:
                continue
        else:
            entry = audit[unit["id"]] = dict(bound, attempts=[], result=None, invalid=False)
        if sum(1 for a in entry["attempts"] if a["not_run"] and "usage limit" not in a["not_run"]) >= MAX_ATTEMPTS:
            print(unit["id"], "audit sessions did not run; stopping", flush=True)
            return 5
        entry["attempts"].append({"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tokens_total": None, "model": None,
                                  "not_run": "interrupted", "invalid": ""})
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(audit, handle, indent=1, ensure_ascii=False)
        root = os.path.join(STATE, "runs", "audit", safe_id(unit), str(int(time.time())))
        work, home, raw = os.path.join(root, "work", "proj"), os.path.join(root, "home"), os.path.join(root, "raw")
        os.makedirs(os.path.dirname(work))
        os.makedirs(home)
        os.makedirs(raw)
        shutil.copytree(arm_dir("N"), work, symlinks=True)
        session = run_codex(work, home, AUDIT_PROMPT % (unit["sessions"][0], unit["hidden_test"]), SESSION_SECONDS,
                            MODELS["codex"], raw, "audit", mode="read-only")
        final = session.pop("final")
        with open(os.path.join(raw, "audit.final.txt"), "w", encoding="utf-8") as handle:
            handle.write(final)
        reason = not_run(session, "codex", MODELS["codex"])
        attempt = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tokens_total": session["tokens_total"],
                   "model": session.get("model"), "not_run": reason, "invalid": ""}
        if not reason:
            reply, attempt["invalid"] = audit_answer(final, report["functions"])
            if reply is not None:
                stated = {f["name"]: f["stated"] for f in reply["functions"]}
                entry["result"] = {"struck": [fn for fn in report["functions"] if not stated[fn]], "answer": reply,
                                   "tokens_total": session["tokens_total"], "model": session.get("model")}
        entry["attempts"][-1] = attempt
        entry["invalid"] = sum(1 for a in entry["attempts"] if a["invalid"]) >= MAX_ATTEMPTS
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(audit, handle, indent=1, ensure_ascii=False)
        if reason:
            print(unit["id"], f"audit not run: {reason}", flush=True)
            return 3 if "usage limit" in reason else 5
        if attempt["invalid"]:
            print(unit["id"], f"audit reply invalid ({attempt['invalid']})" + ("; unit invalid" if entry["invalid"]
                                                                               else "; run audit again"), flush=True)
            if not entry["invalid"]:
                return 5
            continue
        print(unit["id"], "struck", entry["result"]["struck"], flush=True)
    return 0


# ---------------------------------------------------------------- freezing the unit file of a class

def frozen_entry(unit, report, klass):
    """The entry of a unit in a unit file: built only from the candidate and its verification report, so that the
    same candidate and report always give the same entry and the same digest."""
    entry = {key: unit[key] for key in ("id", "type", "sessions", "facts", "superseded_facts", "requirements",
                                        "hidden_test", "reference_patch") if key in unit}
    entry.update(functions=report["functions"], nodes=report["nodes"], items=report["items"],
                 carry="repo" if klass == "B" and unit.get("type") == "handoff" else "home",
                 candidate_sha256=report["sha256"])
    return entry


def counted_rows(tag, cell="codex"):
    """unit -> its single counted row under a tag; two counted rows of a unit, or a row the attempts file does not
    hold, are refused."""
    attempts = read_rows(os.path.join(STATE, f"attempts-{tag}-{cell}.jsonl"))
    counted = {}
    for attempt in attempts:
        if not attempt.get("not_run"):
            if attempt["unit"] in counted:
                raise SystemExit(f"{attempt['unit']} has two counted attempts under tag {tag}")
            counted[attempt["unit"]] = attempt
    rows = {}
    for row in read_rows(os.path.join(STATE, f"rows-{tag}-{cell}.jsonl")):
        if row["unit"] in rows:
            raise SystemExit(f"{row['unit']} has two counted rows under tag {tag}")
        if not any((a["unit"], a["arm"], a["attempt"], a["started"]) == (row["unit"], row["arm"], row["attempt"],
                                                                          row["started"]) and not a.get("not_run")
                   for a in attempts):
            raise SystemExit(f"the {tag} row of {row['unit']} is not in the attempts file")
        rows[row["unit"]] = row
    if set(counted) != set(rows):
        raise SystemExit(f"tag {tag}: counted attempts without a row: {sorted(set(counted) - set(rows))[:3]}")
    return rows


def write_units(out, klass, stage, sources, inputs, notes, units):
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"klass": klass, "stage": stage, "sources": sources, "inputs": inputs, "notes": notes,
                   "units": units}, handle, indent=1, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"out": os.path.basename(out), "sha256": digest(out), "units": [u["id"] for u in units],
                      "notes": notes}, indent=1))


def cmd_freeze(args):
    """Write the unit file of one class by rule. A: the ids given, from --candidates and --verified. B and C: from
    the author ledger in authoring order, each author's candidates and report checked against the ledger and the
    frozen brief. B: per type the first candidate that passed verification and the full-memory solver. C: a unit
    with any function the audit struck, or whose audit replies stayed invalid, is dropped whole; per type the first
    two that were not at ceiling in their one calibration run; after the last supplement a short type is filled up
    to two with its units at ceiling, in authoring order (D42). A short type is written to missing-<class>.json for
    a supplement author. `--stage calibration` writes every class C candidate usable so far."""
    final = args.stage == "final"
    out = os.path.join(STATE, f"units_{args.klass}.json" if final else f"units_{args.klass}_calibration.json")
    if final and main_started():
        raise SystemExit("main runs have started; the unit files are frozen")
    if args.klass == "A":
        if not (args.candidates and args.verified and args.ids) or not final:
            raise SystemExit("class A: give --candidates, --verified and --ids")
        if tuple(args.ids.split(",")) != A_IDS:
            raise SystemExit(f"class A is {','.join(A_IDS)} (PREREG.md), in that order")
        if digest(args.candidates) != A_BANK_SHA256:
            raise SystemExit("class A comes from the frozen tokeneconomizer bank (PREREG.md) only")
        report = checked(args.candidates, args.verified)
        verified = {u["id"]: u for u in report["units"]}
        wanted, units = args.ids.split(","), []
        for unit_id in wanted:
            unit = next((u for u in candidate_units(args.candidates) if u["id"] == unit_id), None)
            if unit is None or not (verified.get(unit_id) or {}).get("valid") \
                    or unit_digest(unit) != verified[unit_id]["sha256"]:
                raise SystemExit(f"class A unit {unit_id} is missing or failed verification")
            units.append(frozen_entry(unit, verified[unit_id], "A"))
        write_units(out, "A", args.stage, [{"candidates_sha256": digest(args.candidates),
                                            "verified_sha256": digest(args.verified)}], {}, {}, units)
        return 0
    if args.candidates or args.verified or args.ids:
        raise SystemExit("classes B and C are frozen from the author ledger; give no files")
    klass, brief = args.klass, digest(brief_path(args.klass))
    counted = counted_authors(klass)
    if not counted:
        raise SystemExit(f"no class {klass} author has run")
    candidates, reports, sources, notes = [], {}, [], {}
    for name, start, end in counted:
        if start["brief_sha256"] != brief:
            raise SystemExit(f"author {name} wrote from another version of AUTHOR_BRIEF_{klass}.md")
        if not (((end or {}).get("files") or {}).get(f"units_{klass}.json") or {}).get("sha256"):
            sources.append({"name": name, "supplies": start.get("supplies"), "brief_sha256": brief,
                            "note": "interrupted" if end is None else "no usable units file"})
            continue
        author_record(klass, name)  # refuses candidates that changed after the author run
        report_file = verified_path(name, klass)
        if not os.path.exists(report_file):
            raise SystemExit(f"author {name}: run `verify --klass {klass} --author {name}` first")
        report = checked(candidates_path(name, klass), report_file)
        for unit in author_units(klass, name):
            if any(unit["id"] == u["id"] for u in candidates):
                raise SystemExit(f"two candidates are called {unit['id']}")
            candidates.append(unit)
        for item in report["units"]:
            reports[item["id"]] = dict(item, verified_file=report_file)
        sources.append({"name": name, "supplies": start.get("supplies"), "brief_sha256": brief,
                        "candidates_sha256": digest(candidates_path(name, klass)),
                        "verified_sha256": digest(report_file)})
    usable = []
    for unit in candidates:
        report = reports.get(unit["id"])
        if not report:
            raise SystemExit(f"{unit['id']} was not verified")
        if unit_digest(unit) != report["sha256"]:
            raise SystemExit(f"{unit['id']} is not the unit that was verified")
        failed = [name for name, good in report["checks"].items() if not good]
        notes[unit["id"]] = "valid" if report["valid"] else "dropped: failed " + ", ".join(failed)
        if report["valid"]:
            usable.append(unit)
    chosen, inputs, missing = [], {}, []
    if klass == "B":
        solver = counted_rows("solver")
        inputs["solver_sha256"] = digest(os.path.join(STATE, "rows-solver-codex.jsonl")) if solver else None
        for kind in TYPES["B"]:
            for unit in (u for u in usable if u.get("type") == kind):
                report = reports[unit["id"]]
                row = solver.get(unit["id"])
                if row is None:
                    raise SystemExit(f"{unit['id']} has no solver result; run `solver --author` first")
                refuse_other(row, bound_to(report, report["verified_file"]), f"the solver result of {unit['id']}")
                if row.get("score") != 1.0:
                    notes[unit["id"]] = f"dropped: full-memory solver scored {row.get('score')}"
                elif any(u.get("type") == kind for u in chosen):
                    notes[unit["id"]] = "valid, spare"
                else:
                    notes[unit["id"]] = "valid, chosen"
                    chosen.append(unit)
            if not any(u.get("type") == kind for u in chosen):
                missing.append(kind)
    else:
        audit_path = os.path.join(STATE, "audit-C.json")
        audit = json.load(open(audit_path, encoding="utf-8")) if os.path.exists(audit_path) else {}
        inputs["audit_sha256"] = digest(audit_path) if os.path.exists(audit_path) else None
        calibration = counted_rows("calibration") if final else {}
        if final:
            inputs["calibration_sha256"] = digest(os.path.join(STATE, "rows-calibration-codex.jsonl")) \
                if calibration else None
        for kind in TYPES["C"]:
            pool = []
            for unit in (u for u in usable if u.get("type") == kind):
                report, entry = reports[unit["id"]], audit.get(unit["id"])
                if entry is None:
                    raise SystemExit(f"{unit['id']} has not been audited")
                refuse_other(entry, bound_to(report, report["verified_file"]), f"the audit of {unit['id']}")
                if entry["invalid"]:
                    notes[unit["id"]] = "dropped: the audit replies broke the schema"
                elif entry["result"] is None:
                    raise SystemExit(f"the audit of {unit['id']} is unfinished")
                elif entry["result"]["struck"]:
                    notes[unit["id"]] = f"dropped: the audit struck {', '.join(entry['result']['struck'])}"
                else:
                    pool.append(unit)
            if not final:
                chosen += pool
                continue
            scores = {}
            for unit in pool:
                row = calibration.get(unit["id"])
                if row is None:
                    raise SystemExit(f"{unit['id']} has no calibration run")
                if row["unit_sha256"] != unit_digest(frozen_entry(unit, reports[unit["id"]], "C")) \
                        or not known_runner(row["runner_sha256"]):
                    raise SystemExit(f"the calibration run of {unit['id']} is of another unit entry or runner")
                scores[unit["id"]] = row.get("score")
            below = [u for u in pool if scores[u["id"]] != 1.0][:2]
            fill = []
            if len(below) < 2 and len(counted) >= MAX_AUTHORS:
                # D42 (owner, 2026-11-11): once the supplements are used up, a short type is filled with its units at
                # ceiling, in authoring order. They may be weaker at showing that O is better (limits in PREREG.md).
                fill = [u for u in pool if scores[u["id"]] == 1.0][:2 - len(below)]
            for unit in pool:
                notes[unit["id"]] = f"calibration {scores[unit['id']]}, " + (
                    "chosen" if unit in below else "chosen: at ceiling, filled after the last supplement (D42)"
                    if unit in fill else "dropped: at ceiling" if scores[unit["id"]] == 1.0 else "spare")
            chosen += below + fill
            if len(below) + len(fill) < 2:
                missing.append(kind)
    if missing:
        names = [name for name, _start, _end in counted]
        with open(missing_path(klass), "w", encoding="utf-8") as handle:
            json.dump({"types": missing, "after_authors": names}, handle, indent=1)
        print(json.dumps({"missing": missing, "notes": notes}, indent=1))
        if len(counted) >= MAX_AUTHORS:
            print(f"class {klass}: no usable {', '.join(missing)} after {len(counted)} author runs; stop and report "
                  "to the owner", flush=True)
        else:
            print(f"class {klass}: no usable {', '.join(missing)}; a new author of the same brief supplies them",
                  flush=True)
        return 7
    if final and os.path.exists(missing_path(klass)):
        os.remove(missing_path(klass))
    order = [c["id"] for c in candidates]
    chosen.sort(key=lambda u: order.index(u["id"]))
    write_units(out, klass, args.stage, sources, inputs, notes,
                [frozen_entry(unit, reports[unit["id"]], klass) for unit in chosen])
    return 0


# ---------------------------------------------------------------- what is frozen before the main runs

def tool_version(argv):
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=120,
                              env=dict(os.environ, LANG="C", LC_ALL="C", LANGUAGE="C"))
        return ((done.stdout or done.stderr).strip().splitlines() or ["unknown"])[0][:80]
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def system_tools():
    """Version and content digest of the system executables the runs use outside the copied tool folders. The OS
    libraries they load are not digested (PREREG states this)."""
    out = {}
    for name in SYSTEM_TOOLS:
        found = shutil.which(name, path="/usr/bin:/bin")
        real = os.path.realpath(found) if found else None
        out[name] = {"path": real, "sha256": digest(real) if real else None,
                     "version": tool_version([real, "--version"]) if real else "missing"}
    return out


def scrub(text):
    """Local paths replaced by the names of the settings they come from, so that the record names no local folder."""
    real = os.path.expanduser("~")
    swaps = [(BIN, "$H1_BIN"), (STATE, "$H1_STATE"), (OAW, "$H1_OAW"), (BASE, "$H1_BASE"), (real, "~")]
    swaps += [(path, f"$H1_HIDE[{i}]") for i, path in enumerate(HIDE)]
    swaps += [(path, f"$H1_RO[{i}]") for i, path in enumerate(SHOW)]
    for path, name in sorted((s for s in swaps if s[0]), key=lambda s: len(s[0]), reverse=True):
        text = text.replace(path, name)
    if os.path.basename(real) and os.path.basename(real) in text:
        raise SystemExit("launch: a local name is left in the launch configuration")
    return text


def cli_file(path):
    """Where an executable the runs start lies: which H1_RO copy, its path there, the file it resolves to inside the
    copy, and that file's digest."""
    for index, shown in enumerate(SHOW):
        if path == shown or path.startswith(shown + os.sep):
            copy = os.path.realpath(in_snapshot(path))
            inside = copy.startswith(os.path.realpath(snapshot(index)) + os.sep)
            return {"ro_index": index, "relative": os.path.relpath(path, shown),
                    "resolved": os.path.relpath(copy, os.path.realpath(snapshot(index))) if inside else "<outside>",
                    "sha256": digest(copy) if inside and os.path.isfile(copy) else None}
    return {"ro_index": None}


def launch_config():
    """How every session and every grading step is started, with local paths replaced by setting names. CLI versions
    are read from the copies the runs see."""
    run = os.path.join(STATE, "runs", "<run>")
    cells = {}
    for cell in ("claude", "codex"):
        argv = claude_argv("<prompt>", MODELS[cell]) if cell == "claude" else codex_argv(MODELS[cell])
        cells[cell] = {"model": MODELS[cell], "cli_version": tool_version([in_snapshot(argv[0]), "--version"]),
                       "cli_file": cli_file(argv[0]),
                       "argv": argv, "prompt_on": "argv" if cell == "claude" else "stdin",
                       "billing_source_required": "none" if cell == "claude" else "chatgpt",
                       "sandbox": sandbox(os.path.join(run, "work", "proj"), os.path.join(run, "home"), cell,
                                          ["<argv>"], prepare=False)}
    config = {"cells": cells,
              "session_environment": environment(),
              "grading": {"environment": environment(tools=False), "pytest": PYTEST,
                          "sandbox": sandbox(os.path.join(run, "grade", "proj"), None, None,
                                             ["/bin/bash", "-c", "<script>"], net=False,
                                             extra=[("--bind", os.path.join(run, "grade", "io"), GRADE)], prepare=False)},
              "audit_argv": codex_argv(MODELS["codex"], "read-only"),
              "limits": {"session_seconds": SESSION_SECONDS, "token_ceiling": CEILING, "max_attempts": MAX_ATTEMPTS,
                         "max_authors": MAX_AUTHORS, "reserve": RESERVE, "first_estimates": ESTIMATE},
              "prompt": PROMPT, "solver_prompt": SOLVER_PROMPT, "audit_prompt": AUDIT_PROMPT, "arms": ARMS,
              "order_offset": OFFSET, "l_policy": L_POLICY, "disallowed_tools": DISALLOWED.split(","),
              "bwrap_version": tool_version(["bwrap", "--version"]),
              "local_settings_sha256": hashlib.sha256(json.dumps([HIDE, SHOW, BIN]).encode()).hexdigest()}
    return json.loads(scrub(json.dumps(config)))


def manifest():
    """Everything a main run depends on, as digests: the frozen files next to this runner, the statistics module and
    oaw_mode.py, the commits, the full content of the arm templates and of the copied tool folders, the suite
    baseline, the budget base, the system executables, the unit files and the launch configuration."""
    here = os.path.dirname(os.path.abspath(__file__))
    recorded = arms_json()
    arms = {arm: arm_facts(arm) for arm in "NOL"}
    for arm, facts in arms.items():
        changed = [key for key, value in facts.items() if recorded["arms"][arm].get(key) != value]
        if changed:
            raise SystemExit(f"arm {arm} is no longer what arms.json recorded: {', '.join(changed)}")
    tools = tools_facts()
    if tools != recorded["tools"]:
        raise SystemExit("a copied tool folder is no longer what arms.json recorded")
    if digest(baseline_path()) != recorded["suite_baseline_sha256"]:
        raise SystemExit("the suite baseline is no longer what arms.json recorded")
    base = json.load(open(budget_path(), encoding="utf-8")) if os.path.exists(budget_path()) else None
    units = {}
    for klass in "ABC":
        path = os.path.join(STATE, f"units_{klass}.json")
        units[klass] = digest(path) if os.path.exists(path) else None
    out = {"files": {name: digest(os.path.join(here, name)) for name in FROZEN},
           "eval_stats_sha256": digest(os.path.join(OAW, "scripts", "eval_stats.py")),
           "oaw_mode_sha256": digest(os.path.join(OAW, "scripts", "oaw_mode.py")),
           "base_commit": BASE_COMMIT, "oaw_commit": recorded["oaw_commit"], "arms": arms, "tools": tools,
           "suite_baseline_sha256": recorded["suite_baseline_sha256"],
           "budget": {key: base[key] for key in ("cap", "decision", "spent_before")} if base else None,
           "system_tools": system_tools(), "units": units, "launch": launch_config()}
    return json.loads(json.dumps(out, sort_keys=True))


def cmd_launch(_args):
    print(json.dumps(launch_config(), indent=1, sort_keys=True))
    return 0


def cmd_manifest(args):
    if args.write and main_started():
        raise SystemExit("main runs have started; the freeze file is not rewritten")
    now = manifest()
    if args.write:
        if not all(now["units"].values()):
            raise SystemExit("a unit file is missing; freeze classes A, B and C first")
        if not now["budget"]:
            raise SystemExit("no budget base; run `budget --spent-before N` first")
        if main_started():
            raise SystemExit("main runs have started; the freeze file is not rewritten")
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(now, handle, indent=1, sort_keys=True)
            handle.write("\n")
        print(os.path.basename(args.out), digest(args.out))
    else:
        print(json.dumps(now, indent=1, sort_keys=True))
    return 0


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("arms")
    sub.add_parser("launch")
    money = sub.add_parser("budget")
    money.add_argument("--spent-before", type=int, help="logical tokens the claude cell used outside this state folder")
    money.add_argument("--raise-to", type=int, help="a new cap, allowed by the owner decision in --decision")
    money.add_argument("--decision")
    verify = sub.add_parser("verify")
    verify.add_argument("--klass", required=True, choices="ABC")
    verify.add_argument("--author", help="classes B and C")
    verify.add_argument("--candidates", help="class A")
    verify.add_argument("--out", help="class A")
    run = sub.add_parser("run")
    run.add_argument("--cell", required=True, choices=("claude", "codex"))
    run.add_argument("--klass", choices="ABC")
    run.add_argument("--units", help="a unit file other than the frozen one of --klass (not for tags main, calibration)")
    run.add_argument("--arms")
    run.add_argument("--only")
    run.add_argument("--tag", default="main")
    run.add_argument("--model")
    sub.add_parser("gate")
    for name in ("solver", "audit"):
        check = sub.add_parser(name)
        check.add_argument("--author", required=True)
    author = sub.add_parser("author")
    author.add_argument("--klass", required=True, choices="BC")
    author.add_argument("--name", required=True)
    author.add_argument("--hours", type=int, default=3)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--klass", required=True, choices="ABC")
    freeze.add_argument("--candidates", help="class A")
    freeze.add_argument("--verified", help="class A")
    freeze.add_argument("--ids", default="", help="class A")
    freeze.add_argument("--stage", default="final", choices=("final", "calibration"))
    record = sub.add_parser("manifest")
    record.add_argument("--write", action="store_true")
    record.add_argument("--out", default=os.path.join(here, "FREEZE.json"))
    args = parser.parse_args()
    for name, value in (("H1_STATE", STATE), ("H1_BASE", BASE), ("H1_OAW", OAW), ("H1_HIDE", HIDE), ("H1_BIN", BIN),
                        ("H1_RO", SHOW)):
        if not value:
            raise SystemExit(f"set {name}")
    return {"arms": cmd_arms, "budget": cmd_budget, "verify": cmd_verify, "run": cmd_run, "solver": cmd_solver,
            "audit": cmd_audit, "freeze": cmd_freeze, "author": cmd_author, "launch": cmd_launch,
            "manifest": cmd_manifest, "gate": cmd_gate}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
