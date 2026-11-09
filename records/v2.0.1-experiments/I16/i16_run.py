"""I16 bug-bash runs (PREREG.md). One tester session per (cell, arm, journey): a fresh workspace with a copy of OAW
(the journey's seeded defect applied, or none for a clean control), the journey's setup already run, and one task.

Arms: N native (task only); C the cheap non-leaking method (one sentence taken from the recipe's own text, frozen
here, added to the task); D the recipe's description only (a skill file holding only its name and description);
F the full recipe (the oaw-bugbash skill as built). D and F get the same pointer line; N and C get none.
Cells: claude (Opus 5.5, claude -p, effort high) and codex (gpt-6.1-sol, codex exec, reasoning high).

Every tester runs inside bubblewrap: the whole filesystem read-only, /tmp and the home folder replaced by empty
tmpfs, the projects folder hidden (records, rubrics, the other repositories), and only the workspace and the host's
own state folder writable. Siblings are invisible. Claude's own Bash sandbox did not engage on this machine
(2026-11-09 test), so the wrapper is the isolation for both cells.

A session that hit a usage limit, used 0 tokens, ended in an error before a result, or billed anything but the
subscription is not a run: deviations.jsonl, and the runner stops (rerun resumes).

    python3 i16_run.py --cell claude --cases FROZEN --oaw-src DIR --skill SKILL.md --claude CLI --out DIR --budget N
    python3 i16_run.py --cell codex  --cases FROZEN --oaw-src DIR --skill SKILL.md --codex CLI --out DIR
Calibration (D32.4): --arms N --reps 3 --only-defect, into its own --out (rep 1 there is a separate run).
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# Folders a tester must not see (records, rubrics, other repositories, credentials files): colon-separated, required.
HIDE = os.environ.get("I16_HIDE", "")
TASK = """You are bug-bashing a command-line tool before its release. Its source is in ./oaw and it is already set up
in this folder as described below. Test it only as a user would: through its commands, their help output and its
documentation (./oaw/README.md and ./oaw/docs/). Do not read or change its source code or tests (./oaw/scripts,
./oaw/templates, ./oaw/tests, ./oaw/vendor) or the copies of its scripts installed into a project. Do not use the
network. You may create, change and delete other files in this folder.

Journey: {goal}

Starting state (these commands were run in this folder before you started):
{setup}

{treatment}Write one JSON report to bugbash_out/report.json with the fields "completed" (boolean), "defects" (array of
objects with "title", "severity" ("critical", "major" or "minor"), "steps", "expected", "observed", "evidence"),
"checked" (array of strings: what you tried) and "notes" (string). Report only behavior you observed. Each defect's
"steps" is the list of exact shell commands, run from this folder in a fresh copy of the starting state, that
reproduce it; they are replayed mechanically there (at most 25 steps, each under 60 seconds, no network). Your final
message gives only the report path and the completion status."""
POINTER = "Use the bug-bash skill for this work: read {path} and follow it.\n\n"
# C: the recipe's adversarial hint alone, from its steps 1 and 3 (written blind to the journeys and defects).
CHEAP = ("Before writing the report, also try relevant adversarial variations such as empty, malformed, oversized or "
         "Unicode input, and check the resulting state against what you expected.\n\n")
LIMIT = re.compile(r"hit your (?:\w+ )?limit|usage limit reached|you've reached your usage limit|limit \W* resets \d", re.I)
SOURCE = r"(?<![!\w.-])(?:\./)?(?:[\w.-]+/)*(?:scripts|templates|tests|vendor)/[\w./*-]+\.(?:py|md|json|sh)\b"
READ_VERB = r"\b(?:cat|less|more|head|tail|sed|awk|grep|egrep|rg|nl|bat|strings|xxd|od|diff|wc|cp|tar|zip)\b"
CD_INTO = re.compile(r"\bcd\s+[^;&|\n]*(?:scripts|templates|tests|vendor)\b"
                     r"|\b(?:workdir|cwd)\\?[\"']?\s*[:=]\s*\\?[\"'][^\"'\\]*(?:scripts|templates|tests|vendor)\b")
BARE_READ = re.compile(READ_VERB + r"[^|;&\n]*(?<![\w/.-])[\w*.-]+\.(?:py|sh)\b")
# Reading the tool's source, not running it: a reading command on a file under scripts/, templates/, tests/ or vendor/
# (in ./oaw or installed into a project, also after a cd), or open() of one. Exclusion globs ("!oaw/scripts/**") and
# invocations ("python3 oaw/scripts/x.py") do not count. Descriptive only: a fixture under a scripts/ folder also counts.
SOURCE_READ = re.compile(READ_VERB + r"[^|;&\n]*" + SOURCE + r"|open\(\s*['\"]" + SOURCE)
READ_TOOLS = ("Read", "Grep", "Glob")


def reads_source(tool, payload):
    """True when one tool call reads the tested tool's source or tests (a black-box breach, recorded, not enforced)."""
    if tool in READ_TOOLS:
        return bool(re.search(SOURCE, " ".join(str(v) for v in (payload or {}).values())))
    text = (payload.get("command", "") if isinstance(payload, dict) else str(payload)) or ""
    if SOURCE_READ.search(text):
        return True
    # after a cd into a source folder, or with a tool call's workdir set there, a reading command on a bare file name
    cd = CD_INTO.search(text)
    return bool(cd and (BARE_READ.search(text, cd.end()) or BARE_READ.search(text[:cd.start()])))


def project_scripts_digest(work):
    """Digest of every scripts/ folder in the workspace outside ./oaw and bugbash_out (the tool installed into a
    project). Commands such as init or migrate may rewrite these legitimately, so a change is recorded, not judged."""
    digest = hashlib.sha256()
    for base, dirs, names in sorted(os.walk(work)):
        rel = os.path.relpath(base, work)
        dirs[:] = sorted(d for d in dirs if not (rel == "." and d in ("oaw", "bugbash_out", ".state")) and d != "__pycache__")
        if os.path.basename(base) == "scripts" or "/scripts/" in f"/{rel}/":
            for name in sorted(names):
                path = os.path.join(base, name)
                if os.path.isfile(path) and not os.path.islink(path):
                    digest.update(os.path.relpath(path, work).encode() + b"\0" + open(path, "rb").read() + b"\0")
    return digest.hexdigest()


def rollout_source_reads(path):
    """Source reads by one Codex thread, from its rollout (shell and exec tool calls)."""
    count = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            payload = json.loads(line).get("payload") or {}
        except ValueError:
            continue
        if payload.get("type") in ("custom_tool_call", "function_call", "local_shell_call"):
            text = payload.get("input") or payload.get("arguments") or json.dumps(payload.get("action") or {})
            count += reads_source("shell", str(text))
    return count


FIRST_ESTIMATE = {"N": 600_000, "C": 600_000, "D": 600_000, "F": 900_000}


def skill_texts(path):
    """(full, description-only) SKILL.md texts. Description-only keeps the frontmatter and repeats the description
    as the whole body, so D sees the same name and description with no instructions."""
    full = open(path, encoding="utf-8").read()
    match = re.match(r"---\n(.*?)\n---\n", full, re.S)
    if not match:
        raise SystemExit(f"{path}: no frontmatter")
    desc = re.search(r"^description:\s*(.+)$", match.group(1), re.M)
    if not desc:
        raise SystemExit(f"{path}: no description")
    return full, f"---\n{match.group(1)}\n---\n\n{desc.group(1).strip()}\n"


def tree_digest(root):
    digest = hashlib.sha256()
    for base, dirs, names in sorted(os.walk(root)):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(names):
            path = os.path.join(base, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            digest.update(os.path.relpath(path, root).encode() + b"\0" + open(path, "rb").read() + b"\0")
    return digest.hexdigest()


def bwrap(work, host, argv, sessions=None):
    """argv wrapped so that only `work` is writable and nothing outside it is visible: the whole filesystem read-only,
    /tmp and the home folder replaced by empty tmpfs (no history, memory, settings or instructions of any earlier
    session), the projects folder hidden. The host gets only its login file, bound (never copied), and Codex a
    per-run sessions folder, so its rollouts are this run's alone."""
    if not any(os.path.isdir(h) for h in HIDE.split(":") if h):
        raise SystemExit("set I16_HIDE to the folders the sandbox must hide (the projects folder at least)")
    home = os.environ["HOME"]
    wrap = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--tmpfs", home]
    for hidden in HIDE.split(":"):
        if hidden and os.path.isdir(hidden) and not os.path.realpath(work).startswith(os.path.realpath(hidden) + "/"):
            wrap += ["--tmpfs", hidden]
    wrap += ["--bind", work, work]
    if host == "claude":
        login = os.path.join(home, ".claude", ".credentials.json")
        wrap += ["--dir", os.path.join(home, ".claude"), "--bind", login, login]
    elif host == "codex":
        login = os.path.join(home, ".codex", "auth.json")
        wrap += ["--dir", os.path.join(home, ".codex"), "--bind", login, login,
                 "--bind", sessions, os.path.join(home, ".codex", "sessions")]
    return wrap + ["--chdir", work, "--die-with-parent", "--unshare-ipc", *argv]


def base_env(work, tool):
    """The environment of the setup, the tester and the replayer: OAW and tool state under ./.state in the workspace
    (the inventory setups export the same values), so every command and every replayed step sees the same state."""
    state = os.path.join(work, ".state")
    return {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TERM": "dumb",
            "PATH": "/usr/bin:/bin" + (":" + os.path.dirname(tool) if tool else ""),  # system python3 first
            "OAW_CONFIG_HOME": os.path.join(state, "config"), "OAW_LAB_HOME": os.path.join(state, "lab"),
            "XDG_CACHE_HOME": os.path.join(state, "cache"), "XDG_DATA_HOME": os.path.join(state, "data"),
            "XDG_CONFIG_HOME": os.path.join(state, "xdg-config"), "TMPDIR": os.path.join(state, "tmp"),
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_ALLOW_PROTOCOL": "file", "GIT_TERMINAL_PROMPT": "0"}


def build(case_dir, oaw_src, work, with_defect=True):
    """A fresh workspace: ./oaw (the defect applied when asked), then the journey's setup, inside the sandbox."""
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    shutil.copytree(oaw_src, os.path.join(work, "oaw"), symlinks=True)
    patch = os.path.abspath(os.path.join(case_dir, "mutation.patch"))
    if with_defect and os.path.exists(patch):
        done = subprocess.run(["patch", "-p1", "--forward", "--batch", "-d", os.path.join(work, "oaw"), "-i", patch],
                              capture_output=True, text=True)
        if done.returncode:
            raise SystemExit(f"{case_dir}: patch failed: {done.stdout[-300:]} {done.stderr[-300:]}")
    journey = json.load(open(os.path.join(case_dir, "journey.json"), encoding="utf-8"))
    os.makedirs(os.path.join(work, ".state", "tmp"), exist_ok=True)
    script = "set -e\n" + "\n".join(journey["setup"]) + "\n"
    done = subprocess.run(bwrap(work, None, ["/bin/bash", "-c", script]), env=base_env(work, ""),
                          capture_output=True, text=True, timeout=300)
    if done.returncode:
        raise SystemExit(f"{case_dir}: setup failed: {done.stderr[-400:]}")
    return {"oaw_digest": tree_digest(os.path.join(work, "oaw")), "journey": journey}


def run_claude(work, prompt, claude, timeout):
    argv = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose", "--model", "claude-opus-5-5",
            "--effort", "high", "--tools", "Bash,Read,Write,Edit,Glob,Grep", "--permission-mode", "bypassPermissions",
            "--setting-sources", "project", "--strict-mcp-config", "--no-session-persistence"]
    started = time.time()
    try:
        done = subprocess.run(bwrap(work, "claude", argv), env=base_env(work, claude), capture_output=True, text=True,
                              timeout=timeout, stdin=subprocess.DEVNULL)
        stdout, code = done.stdout, done.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        code = "timeout"
    row = {"exit": code, "seconds": round(time.time() - started, 1), "raw": stdout, "agents": 0, "tools": {},
           "source_reads": 0}
    final, streamed = "", {}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            row["api_key_source"] = event.get("apiKeySource")
            row["model"] = event.get("model")
            row["claude_code_version"] = event.get("claude_code_version")
        elif event.get("type") == "assistant":
            message = event.get("message", {})
            if message.get("id") and message.get("usage"):
                streamed[message["id"]] = message["usage"]
            for block in message.get("content", []):
                if block.get("type") == "tool_use":
                    row["tools"][block["name"]] = row["tools"].get(block["name"], 0) + 1
                    if reads_source(block["name"], block.get("input") or {}):
                        row["source_reads"] += 1
        elif event.get("type") == "result":
            final = event.get("result", "") or ""
            row["result_seen"], row["is_error"], row["subtype"] = True, event.get("is_error"), event.get("subtype")
            models = event.get("modelUsage") or {}
            row["tokens_total"] = sum(int(m.get(k) or 0) for m in models.values() for k in
                                      ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"))
            row["tokens_noncache"] = sum(int(m.get(k) or 0) for m in models.values() for k in
                                         ("inputTokens", "outputTokens", "cacheCreationInputTokens"))
    if not row.get("tokens_total"):
        row["tokens_total"] = sum(int(u.get(k) or 0) for u in streamed.values() for k in
                                  ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        row["tokens_noncache"] = sum(int(u.get(k) or 0) for u in streamed.values() for k in
                                     ("input_tokens", "output_tokens", "cache_creation_input_tokens"))
        row["tokens_from"] = "stream (lower bound)"
    row["final"] = final[:2000]
    row["limit_seen"] = bool(LIMIT.search(final[:300])) or bool(row.get("is_error") and "limit" in final[:300].lower())
    return row


def rollout_meta(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for _ in range(5):
                event = json.loads(handle.readline() or "{}")
                if event.get("type") == "session_meta":
                    return event.get("payload") or {}
    except (OSError, ValueError):
        return {}
    return {}


def rollout_tokens(path):
    last = None
    for line in open(path, encoding="utf-8", errors="replace"):
        if '"token_count"' in line:
            try:
                info = (json.loads(line).get("payload") or {}).get("info") or {}
            except ValueError:
                continue
            last = info.get("total_token_usage") or last
    if not last:
        return 0, 0
    total = int(last.get("input_tokens") or 0) + int(last.get("output_tokens") or 0)
    return total, total - int(last.get("cached_input_tokens") or 0)


def run_codex(work, prompt, codex, timeout, raw_dir, tag, sessions):
    argv = [codex, "exec", "--json", "--model", "gpt-6.1-sol", "-c", 'model_reasoning_effort="high"',
            "--sandbox", "workspace-write", "--skip-git-repo-check", "--ignore-user-config", "--cd", work, "-"]
    started = time.time()
    try:
        done = subprocess.run(bwrap(work, "codex", argv, sessions), env=base_env(work, codex), input=prompt, capture_output=True,
                              text=True, timeout=timeout)
        stdout, code, stderr = done.stdout, done.returncode, done.stderr
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        code = "timeout"
    row = {"exit": code, "seconds": round(time.time() - started, 1), "raw": stdout, "agents": 0, "tools": {},
           "api_key_source": "chatgpt", "model": "gpt-6.1-sol", "stderr_tail": stderr[-400:], "source_reads": 0}
    texts, errors, root_id = [], [], None
    parent = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "thread.started":
            root_id = event.get("thread_id")
        elif kind == "item.completed":
            item = event.get("item") or {}
            itype = item.get("type")
            if itype == "agent_message" and str(item.get("text", "")).strip():
                texts.append(item["text"])
            elif itype and itype != "reasoning":
                row["tools"][itype] = row["tools"].get(itype, 0) + 1  # source reads: from the rollouts (workdir kept)
        elif kind == "turn.completed":
            row["result_seen"] = True
            for key in parent:
                parent[key] += int((event.get("usage") or {}).get(key) or 0)
        elif kind in ("turn.failed", "error"):
            errors.append(json.dumps(event)[:300])
    # Every rollout in the per-run sessions folder belongs to this run: the root thread and all its descendants,
    # wherever they worked. All are kept and all are billed; agents are the non-root threads.
    found = {p: rollout_meta(p) for p in glob.glob(os.path.join(sessions, "**", "rollout-*.jsonl"), recursive=True)}
    keep = os.path.join(raw_dir, f"{tag}-rollouts")
    os.makedirs(keep, exist_ok=True)
    totals = []
    for path, meta in found.items():
        dest = os.path.join(keep, os.path.basename(path))
        shutil.move(path, dest)
        totals.append((meta.get("id") == root_id, rollout_tokens(dest)))
        row["source_reads"] += rollout_source_reads(dest)  # every thread, with each tool call's workdir
    row["threads"] = len(totals)
    row["agents"] = sum(1 for is_root, _t in totals if not is_root)
    root = [t for is_root, t in totals if is_root]
    if root and root[0][0]:
        row["tokens_from"] = "rollouts (all threads of the run)"
        base = root[0]
    else:
        base = (parent["input_tokens"] + parent["output_tokens"],
                parent["input_tokens"] - parent["cached_input_tokens"] + parent["output_tokens"])
        row["tokens_from"] = "parent stream + other rollouts"
    row["tokens_total"] = base[0] + sum(t[0] for is_root, t in totals if not is_root)
    row["tokens_noncache"] = base[1] + sum(t[1] for is_root, t in totals if not is_root)
    row["final"] = (texts[-1] if texts else "")[:2000]
    row["errors"] = errors
    row["is_error"] = bool(errors) and not row.get("result_seen")
    row["limit_seen"] = bool(LIMIT.search(" ".join(errors) + " " + stderr[-600:]))
    return row


def not_run(row, cell):
    if cell == "claude" and row.get("api_key_source") not in ("none",):
        return f"billing source {row.get('api_key_source')}"
    if row["limit_seen"]:
        return "usage limit"
    if not row.get("tokens_total"):
        return "0 tokens"
    if row["exit"] == "timeout":
        return ""  # a timeout is a run; its report, if any, is graded
    if not row.get("result_seen") or row.get("is_error") or row["exit"] != 0:
        return f"error (exit {row['exit']}, subtype {row.get('subtype')})"
    return ""


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell", choices=("claude", "codex"), required=True)
    parser.add_argument("--cases", required=True, help="frozen folder: spec.json and cases/<id>/")
    parser.add_argument("--oaw-src", required=True, help="git archive of OAW at the frozen commit")
    parser.add_argument("--skill", required=True, help="the frozen oaw-bugbash SKILL.md")
    parser.add_argument("--claude", default="")
    parser.add_argument("--codex", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--budget", type=int, default=0, help="claude cell: stop before a run that may pass this")
    parser.add_argument("--spent", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--arms", default="N,C,D,F")
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--only-defect", action="store_true", help="calibration: defect journeys only")
    parser.add_argument("--only", default="", help="arm:journey,... (pilots, partitions)")
    args = parser.parse_args(argv)
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "OPENAI_API_KEY"):
        if os.environ.get(key):
            raise SystemExit(f"{key} is set; subscription only")
    spec_path = os.path.join(args.cases, "spec.json")
    spec = json.load(open(spec_path, encoding="utf-8"))
    order = [j for j in spec["order"] if not args.only_defect or spec["kinds"][j] == "defect"]
    full, desc_only = skill_texts(args.skill)
    if hashlib.sha256(full.encode()).hexdigest() != spec["skill_sha256"]:
        raise SystemExit("the skill file differs from the frozen spec")
    raw_dir = os.path.join(args.out, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    rows_path, dev_path = os.path.join(args.out, "rows.jsonl"), os.path.join(args.out, "deviations.jsonl")
    only = set(filter(None, args.only.split(",")))
    runner_sha = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    spec_sha = hashlib.sha256(open(spec_path, "rb").read()).hexdigest()
    oaw_sha = tree_digest(args.oaw_src)
    if oaw_sha != spec["oaw_src_digest"]:
        raise SystemExit("the OAW source differs from the frozen spec")
    skill_dir = ".claude/skills/oaw-bugbash" if args.cell == "claude" else ".agents/skills/oaw-bugbash"
    arms = [a for a in ("N", "C", "D", "F") if a in set(args.arms.split(","))]
    prompts = {}
    for arm in arms:
        pointer = {"N": "", "C": CHEAP}.get(arm, POINTER.format(path=f"{skill_dir}/SKILL.md"))
        prompts[arm] = lambda goal, setup, pointer=pointer: TASK.format(goal=goal, setup=setup, treatment=pointer)
    prompt_sha = {arm: hashlib.sha256(prompts[arm]("{goal}", "{setup}").encode()).hexdigest() for arm in arms}
    base = tempfile.mkdtemp(prefix="i16-", dir=os.environ.get("I16_WS_ROOT") or None)

    def ledger():
        spent, done, largest = args.spent, set(), dict(FIRST_ESTIMATE)
        for name in ("rows.jsonl", "deviations.jsonl"):
            path = os.path.join(args.out, name)
            if not os.path.exists(path):
                continue
            for line in open(path, encoding="utf-8"):
                row = json.loads(line)
                spent += row.get("tokens_total") or 0
                largest[row["arm"]] = max(largest.get(row["arm"], 0), row.get("tokens_total") or 0)
                if name == "rows.jsonl":
                    if (row.get("runner_sha256") != runner_sha or row.get("prompt_sha256") != prompt_sha.get(row["arm"])
                            or row.get("spec_sha256") != spec_sha):
                        raise SystemExit(f"{path}: {row['arm']}-{row['id']} came from another runner, prompt or spec")
                    done.add((row["arm"], row["id"], row.get("rep", 1)))
        return spent, done, largest

    for index, jid in enumerate(order):
        rotation = arms[index % len(arms):] + arms[:index % len(arms)]
        for rep, arm in [(r, a) for r in range(1, args.reps + 1) for a in rotation]:
            spent, done, largest = ledger()
            if (arm, jid, rep) in done or (only and f"{arm}:{jid}" not in only):
                continue
            if args.cell == "claude" and args.budget and spent + largest[arm] > args.budget:
                print(f"budget guard: {spent:,} spent, {arm} {jid} needs about {largest[arm]:,}; stopping", flush=True)
                return 3
            key = f"{arm}-{jid}" + (f".r{rep}" if args.reps > 1 else "")
            # a random, non-adjacent folder per run: no run can see another (the sandbox also hides siblings)
            work = tempfile.mkdtemp(prefix="ws-", dir=base)
            case_dir = os.path.join(args.cases, "cases", jid)
            if tree_digest(case_dir) != spec["case_digests"][jid]:
                raise SystemExit(f"{jid}: case files differ from the frozen spec")
            facts = build(case_dir, args.oaw_src, work)
            if facts["oaw_digest"] != spec["built_digests"][jid]:
                raise SystemExit(f"{jid}: built tool differs from the frozen spec")
            if arm in ("D", "F"):
                os.makedirs(os.path.join(work, skill_dir))
                open(os.path.join(work, skill_dir, "SKILL.md"), "w", encoding="utf-8").write(full if arm == "F" else desc_only)
            journey = facts.pop("journey")
            scripts_before = project_scripts_digest(work)
            prompt = prompts[arm](journey["goal"], "\n".join(f"  {c}" for c in journey["setup"]))
            attempt = len([n for n in os.listdir(raw_dir) if n.startswith(f"{key}.a") and n.endswith(".jsonl")]) + 1
            tag = f"{key}.a{attempt}"
            if args.cell == "claude":
                row = run_claude(work, prompt, args.claude, args.timeout)
            else:
                sessions = tempfile.mkdtemp(prefix="sessions-", dir=base)
                row = run_codex(work, prompt, args.codex, args.timeout, raw_dir, tag, sessions)
                shutil.rmtree(sessions, ignore_errors=True)
            with open(os.path.join(raw_dir, f"{tag}.jsonl"), "w", encoding="utf-8") as handle:
                handle.write(row.pop("raw"))
            row.update({"cell": args.cell, "arm": arm, "id": jid, "rep": rep, "attempt": attempt,
                        "kind": spec["kinds"][jid], "prompt_sha256": prompt_sha[arm], "runner_sha256": runner_sha,
                        "spec_sha256": spec_sha, "oaw_src_digest": oaw_sha, "built_digest": facts["oaw_digest"]})
            try:
                row["report"] = json.load(open(os.path.join(work, "bugbash_out", "report.json"), encoding="utf-8"))
            except (OSError, ValueError) as exc:
                row["report"], row["report_error"] = None, str(exc)[:200]
            row["tool_changed"] = tree_digest(os.path.join(work, "oaw")) != facts["oaw_digest"]
            row["case_digest"] = spec["case_digests"][jid]
            row["project_scripts_changed"] = project_scripts_digest(work) != scripts_before
            keep = os.path.join(raw_dir, f"{tag}-bugbash_out")
            shutil.rmtree(keep, ignore_errors=True)
            if os.path.isdir(os.path.join(work, "bugbash_out")):
                shutil.copytree(os.path.join(work, "bugbash_out"), keep, symlinks=True)
            shutil.rmtree(work, ignore_errors=True)
            reason = not_run(row, args.cell)
            if reason:
                with open(dev_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(dict(row, reason=reason), ensure_ascii=False) + "\n")
                print(f"{args.cell} {tag}: not a run ({reason}); stopping, rerun to resume", flush=True)
                return 4 if reason.startswith("billing") else 5
            with open(rows_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"{args.cell} {tag}: exit {row['exit']} {row['seconds']}s report "
                  f"{'ok' if row['report'] else 'MISSING'} defects {len((row['report'] or {}).get('defects') or [])} "
                  f"source_reads {row['source_reads']} tokens {row['tokens_total']:,} (non-cache "
                  f"{row['tokens_noncache']:,}) spent {ledger()[0]:,}", flush=True)
    shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
