#!/usr/bin/env python3
"""cap_run: the runner of the capability tasting, PPT domain (capability/PLAN.md). It reuses the H1 runner's stream
parsing, token accounting and ledgers (records/v2.0.1-experiments/H1/h1_run.py, loaded as a module) and replaces its
sandbox, launch lines and grading.

Groups: N (the shared tools only; run twice as N1 and N2) and one group per candidate (P1, P2, P3: N plus the
candidate's install template). Cells: claude (Claude Code, Opus 5.5, effort high) and codex (Codex CLI, gpt-6.1-sol,
reasoning high). One session per run; nothing is resumed.

Every session runs inside bubblewrap in a network namespace of its own. The sandbox starts from an empty root and
shows only: the system folders in SYSTEM_DIRS read-only, a fresh /tmp and /dev, the copied tool folders at their own
paths, a fresh working folder and a fresh home, the group's template mounted read-only at the paths an install would
use, and the login file. Nothing else of the machine exists inside it: no task store, no other run, no host home, no
host socket. The only way out is cap_net.py: a forwarder inside the sandbox and an allowlist proxy outside it.
Grading runs in the same sandbox with no proxy, no login and the N template.

Configuration is taken from the environment so that no local path is written into the records:
  CAP_STATE      state root (ledgers, tasks, what is kept of every run)
  CAP_SCRATCH    a folder on a local disk for the working folder and home of a running session; emptied after it
  CAP_SNAP       where `setup` keeps its copies of the CAP_RO folders
  CAP_TEMPLATES  the install templates: common/ and one folder per candidate, each with a template.json
  CAP_BASE       the idle-check corpus at the H1 base commit with its .venv built for /home/dev/proj
  CAP_IDLE_UNITS the frozen H1 class A unit file
  CAP_RO         colon-separated folders shown read-only at the same path, from their copies in CAP_SNAP
  CAP_BIN        the folder holding the claude and codex executables (inside one of the CAP_RO folders)

Order of work: setup (copies, idle corpus, and the lock: digests of the plan, the brief, the programs, the templates
and the tools; nothing locked may change afterwards in this state folder), budget, warm, probe, author, verify,
run --tag calibration, select, manifest --write (FREEZE.json), run --tag main. See PLAN.md.
"""
import argparse
import concurrent.futures
import errno
import fcntl
import glob
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))

STATE = os.environ.get("CAP_STATE", "")
SCRATCH = os.environ.get("CAP_SCRATCH", "")
SNAP = os.environ.get("CAP_SNAP", "")
TEMPLATES = os.environ.get("CAP_TEMPLATES", "")
BASE = os.environ.get("CAP_BASE", "")
IDLE_UNITS = os.environ.get("CAP_IDLE_UNITS", "")
SHOW = [p for p in os.environ.get("CAP_RO", "").split(":") if p]
BIN = os.environ.get("CAP_BIN", "")
H1_FILE = os.path.join(HERE, "..", "H1", "h1_run.py")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


h1 = load_module("h1_run", H1_FILE)

HOME, WORK, IDLE_WORK, GRADE, NET = "/home/dev", "/home/dev/work", "/home/dev/proj", "/home/dev/grade", "/tmp/capnet"
# All that a sandbox sees of the machine, read-only. Everything else does not exist inside it.
SYSTEM_DIRS = ("/usr", "/bin", "/sbin", "/lib", "/lib32", "/lib64", "/libx32", "/etc", "/opt/google",
               "/var/cache/fontconfig", "/sys/devices/system/cpu")
PORT = 18080
MODELS = {"claude": "claude-opus-5-5", "codex": "gpt-6.1-sol"}
CANDIDATES = ("P1", "P2", "P3")
MAX_UNITS = 3                  # units of one candidate (D21)
# The one running order of a cell (PLAN.md section 10): N twice on the four tasks, N on the two idle tasks, then
# each candidate's four tasks followed by its two idle tasks.
SEQUENCE = [("N1", "answer"), ("N2", "answer"), ("N", "idle")] + [(c, k) for c in CANDIDATES for k in ("answer", "idle")]
IDLE_IDS = ("t01", "t04")
TASKS = 4                      # tasks of the domain
AUTHOR_TASKS = 6               # tasks one author writes; the first four that qualify are taken, in the author's order
MAX_AUTHORS = 3                # the first author and at most two supplements
# Hosts a session may reach: the CLI's model endpoint and its sign-in. Everything else is refused by the proxy.
ALLOW = {"claude": ["api.anthropic.com:443", "console.anthropic.com:443", "platform.claude.com:443"],
         "codex": ["chatgpt.com:443", "auth.openai.com:443", "api.openai.com:443"]}
PROMPT = "你在目前的工作目錄裡工作，素材在 inputs/ 資料夾。\n\n{task}"
DISALLOWED = h1.DISALLOWED
# What Claude Code lists at startup is not fixed by the group alone (probe history, 2026-11-12): three commands
# behind a remote flag (among them the skill `schedule`, about 134 tokens) and two usage commands that depend on
# cached account state (about 221 tokens) are in the first request or not, depending on what has arrived when the
# session starts. Two measures make the first request of N and of a candidate differ only by the candidate
# (PLAN.md section 3: the built-in skills of the groups must be the same):
#  - every claude home starts with the same CLI state file, written by two warm-up sessions (`warm`);
#  - a session whose startup lists are not the frozen ones of its group is stopped at once and started again;
#    such a start costs nothing and is counted apart from the MAX_ATTEMPTS failures, at most MAX_RESTARTS times.
MAX_RESTARTS = 10
STARTUP = "startup lists"
SESSION_SECONDS = 7200         # as in H1; a session that reaches it is cut and its deliverable is graded as it stands
CEILING = 3_000_000            # logical tokens in one claude session; the same treatment as the time limit
MAX_ATTEMPTS = 3               # attempts of one (cell, group, unit) that may fail for infrastructure reasons
CAP = 30_000_000               # logical tokens the claude cell may spend on this domain, every attempt counted (D35)
CAP_DECISION = "D35"
STOP_LINE = 27_000_000         # spent + RESERVE x the next run's estimate above this: stop, in sequence
RESERVE = 1.25
ESTIMATE = {"answer": 1_000_000, "idle": 400_000, "probe": 60_000}
IDLE_RATIO = 1.02
CODEX_SLOTS = 2                # codex sessions of this state folder that may run at the same time
CELLS_AT_ONCE = 2              # runs that may hold scratch space at the same time (one per cell)
DISK_SAFETY = 15 * 1024 ** 3   # bytes that must stay free beyond what the runs need (PLAN.md section 10)
DISK_FIRST_PEAK = 2 * 1024 ** 3   # peak scratch of one run before any was measured
DISK_FIRST_KEPT = 256 * 1024 ** 2  # what one run keeps before any was measured
KEEP_WORK_BYTES = 20 * 1024 ** 2   # a working folder larger than this is listed, not kept
SCRATCH_FLOOR = 1024 ** 3      # less than this free on the scratch disk after a session: the session may have run
                               # out of space inside its sandbox, where the runner cannot see it; the run does not count
EXEMPT = ("usage limit", "budget cap", "no space", STARTUP)   # reasons outside the MAX_ATTEMPTS failures
SYSTEM_TOOLS = ("git", "bash", "python3", "bwrap", "timeout", "soffice", "pdftotext", "pdftoppm", "pdftohtml")
LOCKED_FILES = ("PLAN.md", "AUTHOR_BRIEF_PPT.md", "cap_run.py", "cap_net.py", "ppt_check.py", "cap_judge.py")
# Tool calls that name a candidate, counted per session as a description of whether it was used.
h1.EVIDENCE = {"officecli": re.compile(r"officecli"),
               "huashu-design": re.compile(r"huashu-design|html2pptx|export_deck_pptx|pptx_from_rendered"),
               "professional-pptx": re.compile(r"professional-pptx|build_pptx\.py|lint_pptx\.py")}
h1.CEILING = CEILING


class Ctx:
    """What the sandbox of the next call looks like."""
    group = "N"
    workdir = WORK
    netdir = None
    idle = False


def digest(path):
    return h1.digest(path)


def tree_digest(root):
    return h1.tree_digest(root)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def append(path, row):
    h1.append(path, row)


def read_rows(path):
    return h1.read_rows(path)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=1, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    return json.load(open(path, encoding="utf-8"))


def tree_bytes(root):
    total = 0
    for base, _dirs, names in os.walk(root):
        for name in names:
            path = os.path.join(base, name)
            if not os.path.islink(path):
                try:
                    total += os.path.getsize(path)
                except OSError:
                    pass
    return total


# ---------------------------------------------------------------- sandbox

def snapshot(index):
    return os.path.join(SNAP, str(index))


def template(group):
    """template.json of a candidate group or of the shared tools ('common')."""
    return read_json(os.path.join(TEMPLATES, group, "template.json"), {})


def mounts(group):
    """(source, target) of everything mounted read-only for a group: the shared tools, then the candidate's."""
    names = ["common"] + ([group] if group in CANDIDATES else [])
    return [(os.path.join(TEMPLATES, name, source), target) for name in names
            for source, target in template(name).get("mounts", [])]


def within(path, folder):
    path, folder = os.path.realpath(path), os.path.realpath(folder)
    return path == folder or path.startswith(folder + os.sep)


def guard_paths():
    """Refuse a configuration in which a sandbox could read what it must not: the state, the scratch folder, the
    templates, the tool copies, this folder (plan, checks, references), the corpus, the unit file or the user's home
    must not lie inside a folder that every sandbox sees."""
    private = {"CAP_STATE": STATE, "CAP_SCRATCH": SCRATCH, "CAP_SNAP": SNAP, "CAP_TEMPLATES": TEMPLATES,
               "the records folder": HERE, "CAP_BASE": BASE, "CAP_IDLE_UNITS": IDLE_UNITS,
               "the home folder": os.path.expanduser("~")}
    for name, path in private.items():
        for seen in list(SYSTEM_DIRS) + SHOW:
            if within(path, seen):
                raise SystemExit(f"{name} lies inside {seen}, which every sandbox can read")
            # a folder shown to every sandbox must not hold private data either; a tool folder inside the home
            # folder is the one exception (it shows itself and nothing else of the home)
            if name != "the home folder" and within(seen, path):
                raise SystemExit(f"{seen}, which every sandbox can read, lies inside {name}")
    if not any(within(BIN, shown) for shown in SHOW):
        raise SystemExit("CAP_BIN must lie inside a folder of CAP_RO, so that the copy covers both CLIs")


def sandbox(work, home, host, argv, *, net=True, extra=(), prepare=True):
    """argv wrapped so that it sees the system folders, the tool copies and the group's template read-only, a
    writable `work` and `home`, and nothing else; no network. With `net` and a proxy folder in Ctx, the session is
    started by the forwarder of cap_net.py."""
    real = os.path.expanduser("~")
    wrap = ["bwrap"]
    for folder in SYSTEM_DIRS:
        if not prepare or os.path.isdir(folder):
            wrap += ["--ro-bind", folder, folder]
    wrap += ["--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--dir", "/var/tmp", "--dir", "/run"]
    for index, shown in enumerate(SHOW):
        if prepare and not os.path.isdir(snapshot(index)):
            raise SystemExit(f"no copy of CAP_RO[{index}]; run `setup` first")
        wrap += ["--ro-bind", snapshot(index), shown]
    wrap += ["--bind", home, HOME] if home else ["--dir", HOME]
    wrap += ["--bind", work, Ctx.workdir]
    for source, target in mounts(Ctx.group):
        wrap += ["--ro-bind", source, target]
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
    wrap += ["--unshare-net"]
    if net and (Ctx.netdir or not prepare):
        wrap += ["--ro-bind", Ctx.netdir or "<proxy folder>", NET]
        argv = ["/usr/bin/python3", "-I", f"{NET}/cap_net.py", "forward", str(PORT), f"{NET}/proxy.sock", "--", *argv]
    return wrap + ["--chdir", Ctx.workdir, "--die-with-parent", "--unshare-ipc", "--unshare-pid", *argv]


def environment(tools=True):
    """The environment of a session (tools=True: the CLIs on PATH and the proxy variables) or of a grading step."""
    path = f"{HOME}/.local/bin:/usr/bin:/bin" + (f":{BIN}" if tools and BIN else "")
    env = {"HOME": HOME, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TERM": "dumb", "DISABLE_AUTOUPDATER": "1",
           "PATH": path, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_AUTHOR_NAME": "dev",
           "GIT_AUTHOR_EMAIL": "dev@example.invalid", "GIT_COMMITTER_NAME": "dev",
           "GIT_COMMITTER_EMAIL": "dev@example.invalid", "OFFICECLI_SKIP_UPDATE": "1"}
    if Ctx.idle:
        env.update(VIRTUAL_ENV=f"{IDLE_WORK}/.venv", PATH=f"{IDLE_WORK}/.venv/bin:" + path)
    if tools:
        proxy = f"http://127.0.0.1:{PORT}"
        env.update(HTTPS_PROXY=proxy, HTTP_PROXY=proxy, https_proxy=proxy, http_proxy=proxy,
                   CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1")
    return env


def claude_argv(prompt, model):
    return [os.path.join(BIN, "claude"), "-p", prompt, "--output-format", "stream-json", "--verbose", "--model", model,
            "--effort", "high", "--permission-mode", "bypassPermissions", "--setting-sources", "user,project",
            "--strict-mcp-config", "--disallowedTools", DISALLOWED]


def codex_argv(model, mode="danger-full-access"):
    # The session's sandbox is the one above; Codex's own is off so that the shared tools and a candidate's tools
    # can write to the home folder, as they can in the claude cell.
    return [os.path.join(BIN, "codex"), "exec", "--json", "--model", model, "-c", 'model_reasoning_effort="high"',
            "--sandbox", mode, "--skip-git-repo-check", "--cd", Ctx.workdir, "-"]


h1.sandbox, h1.environment, h1.claude_argv, h1.codex_argv = sandbox, environment, claude_argv, codex_argv
_stream = h1.stream
GUARD = {"lists": None}     # the startup lists the next claude session must show, or None


def startup_lists(event):
    """The skills and slash commands of a Claude Code init event, sorted."""
    return {"skills": sorted(str(s) for s in event.get("skills") or []),
            "commands": sorted(str(c) for c in event.get("slash_commands") or [])}


def guarded_stream(argv, env, stdin_text, timeout, watch=None, tee=None):
    """The H1 stream with one more watcher: a claude session whose init event lists other skills or commands than
    the guard asks for is stopped before it does any work."""
    def both(line):
        if GUARD["lists"] is not None and '"init"' in line and '"slash_commands"' in line:
            for event in h1.events([line]):
                if event.get("subtype") == "init" and startup_lists(event) != GUARD["lists"]:
                    return STARTUP
        return watch(line) if watch else None
    return _stream(argv, env, stdin_text, timeout, both, tee)


h1.stream = guarded_stream


def offline(work, script, *, io=None, timeout=2400, group="N", workdir=WORK, idle=False, extra=()):
    """A shell script with no network, no login and an empty home (grading, queries)."""
    Ctx.group, Ctx.workdir, Ctx.netdir, Ctx.idle = group, workdir, None, idle
    binds = ([("--bind", io, GRADE)] if io else []) + list(extra)
    try:
        done = subprocess.run(sandbox(work, None, None, ["/bin/bash", "-c", script], net=False, extra=binds),
                              env=environment(tools=False), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    return done.returncode, done.stdout, done.stderr


class Proxy:
    """The allowlist proxy of one session: a folder with its socket and the forwarder, and its log."""

    def __init__(self, cell, log):
        self.folder = os.path.join(SCRATCH, "net", f"{os.getpid()}-{int(time.time() * 1000) % 10 ** 9}")
        os.makedirs(self.folder)
        shutil.copyfile(os.path.join(HERE, "cap_net.py"), os.path.join(self.folder, "cap_net.py"))
        self.log = log
        self.process = subprocess.Popen([sys.executable, "-I", os.path.join(HERE, "cap_net.py"), "serve",
                                         os.path.join(self.folder, "proxy.sock"), log, *ALLOW[cell]],
                                        stdout=subprocess.PIPE, text=True)
        if self.process.stdout.readline().strip() != "ready":
            raise SystemExit("the proxy did not start")

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
        shutil.rmtree(self.folder, ignore_errors=True)

    def summary(self):
        allowed, refused = {}, {}
        for row in read_rows(self.log):
            key = f"{row.get('host')}:{row.get('port')}"
            target = allowed if row.get("allowed") else refused
            target[key] = target.get(key, 0) + 1
        return {"allowed": allowed, "refused": refused}


class codex_slot:
    """At most CODEX_SLOTS codex sessions of this state folder at the same time."""

    def __enter__(self):
        while True:
            for index in range(CODEX_SLOTS):
                handle = open(os.path.join(STATE, f"codex-slot-{index}.lock"), "w")
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.handle = handle
                    return self
                except OSError:
                    handle.close()
            time.sleep(20)

    def __exit__(self, *_exc):
        self.handle.close()


# ---------------------------------------------------------------- sessions

def startup_claude(raw):
    """Input tokens (cache included) of the session's first model call: the first main-thread message."""
    if not os.path.exists(raw):
        return None
    for event in h1.events(open(raw, encoding="utf-8", errors="replace")):
        if event.get("type") != "assistant" or event.get("parent_tool_use_id") is not None:
            continue
        message = event.get("message") or {}
        usage = message.get("usage")
        if message.get("model") != "<synthetic>" and isinstance(usage, dict):
            return sum(int(usage.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens",
                                                         "cache_read_input_tokens"))
    return None


def startup_codex(raw, rollouts):
    """Input tokens (cached included) of the first model call of the root thread, from its rollout."""
    root_id = None
    if os.path.exists(raw):
        for event in h1.events(open(raw, encoding="utf-8", errors="replace")):
            if event.get("type") == "thread.started":
                root_id = event.get("thread_id")
                break
    for path in sorted(glob.glob(os.path.join(rollouts, "rollout-*.jsonl"))):
        thread, first = None, None
        for event in h1.events(open(path, encoding="utf-8", errors="replace")):
            payload = event.get("payload") or {}
            if event.get("type") == "session_meta" and isinstance(payload, dict):
                thread = payload.get("id")
            elif isinstance(payload, dict) and payload.get("type") == "token_count" and first is None:
                info = payload.get("info") or {}
                usage = info.get("last_token_usage") or info.get("total_token_usage")
                if isinstance(usage, dict) and usage.get("input_tokens"):
                    first = int(usage["input_tokens"])
        if root_id and thread == root_id:
            return first
    return None


def init_lists(raw):
    """The startup lists of a claude session from its raw stream, or None."""
    if os.path.exists(raw):
        for event in h1.events(line for line in open(raw, encoding="utf-8", errors="replace") if '"init"' in line):
            if event.get("subtype") == "init":
                return startup_lists(event)
    return None


def run_session(cell, group, work, home, prompt, raw, name, *, idle=False, allow=None, model=None, seconds=None,
                lists=None):
    """One session behind the proxy. Returns the H1 session row with the proxy summary, the mounts, PATH, the
    startup tokens and (claude) the startup lists added. `lists`: the startup lists a claude session must show."""
    model = model or MODELS[cell]
    seconds = seconds or SESSION_SECONDS
    proxy = Proxy(cell, os.path.join(raw, f"{name}.net.jsonl"))
    Ctx.group, Ctx.workdir, Ctx.netdir, Ctx.idle = group, (IDLE_WORK if idle else WORK), proxy.folder, idle
    try:
        if cell == "claude":
            GUARD["lists"] = lists
            try:
                session = h1.run_claude(work, home, prompt, seconds, model, raw, name, allow)
            finally:
                GUARD["lists"] = None
            session["startup_tokens"] = startup_claude(os.path.join(raw, f"{name}.jsonl"))
            session["startup_lists"] = init_lists(os.path.join(raw, f"{name}.jsonl"))
        else:
            with codex_slot():
                session = h1.run_codex(work, home, prompt, seconds, model, raw, name, "danger-full-access")
            session["startup_tokens"] = startup_codex(os.path.join(raw, f"{name}.jsonl"),
                                                      os.path.join(raw, f"{name}-rollouts"))
        session["path"] = environment()["PATH"].replace(BIN, "$CAP_BIN") if BIN else environment()["PATH"]
    finally:
        proxy.close()
        Ctx.netdir = None
    session["net"] = proxy.summary()
    session["mounts"] = [target for _source, target in mounts(group)]
    return session


def warm_path():
    return os.path.join(STATE, "warm", "claude.json")


def fresh_home(home, cell=None, warm=True):
    """An empty home. A claude home starts with the CLI state file that `warm` wrote, the same in every group."""
    for name in (".claude", ".codex", ".agents", ".cache", ".config", ".local"):
        os.makedirs(os.path.join(home, name), exist_ok=True)
    if cell == "claude" and warm:
        if not os.path.exists(warm_path()):
            raise SystemExit("no warm CLI state; run `warm` first")
        shutil.copyfile(warm_path(), os.path.join(home, ".claude.json"))


def group_of(arm):
    return "N" if arm in ("N", "N1", "N2") else arm


def frozen_entry(cell, group):
    """What the probe recorded for this cell and group, or {}."""
    data = read_json(os.path.join(STATE, f"probe-{cell}.json"), {})
    return (data.get("groups") or {}).get(group) or {}


# ---------------------------------------------------------------- grading

def grade_answer(task_dir, work, out_dir):
    """Grade <work>/output.pptx with the task's check in a sandbox without network. The deliverable is kept bit for
    bit together with small pictures of its slides; the variant decks and PDFs of the check are removed."""
    io, ro, keep = os.path.join(out_dir, "io"), os.path.join(out_dir, "ro"), os.path.join(out_dir, "deliverable")
    for folder in (io, ro, keep):
        os.makedirs(folder)
    shutil.copyfile(os.path.join(HERE, "ppt_check.py"), os.path.join(ro, "ppt_check.py"))
    shutil.copyfile(os.path.join(task_dir, "check.py"), os.path.join(ro, "check.py"))
    # Amendment 1 (before any calibration): a task's check may read the task's own input material, which stands
    # beside it as it did where the author wrote and tried the check. Read-only, and only in the grading sandbox.
    shutil.copytree(os.path.join(task_dir, "inputs"), os.path.join(ro, "inputs"))
    source = os.path.join(work, "output.pptx")
    result = {"pass": False, "deliverable": False, "error": "no deliverable", "failures": [], "task_failures": []}
    sha = None
    if os.path.isfile(source) and not os.path.islink(source):
        shutil.copyfile(source, os.path.join(keep, "output.pptx"))
        shutil.copyfile(source, os.path.join(io, "output.pptx"))
        sha = digest(source)
        script = (f"cd {WORK} && python3 {GRADE}/ppt_check.py grade {WORK}/output.pptx {GRADE}/check.py {WORK}/tmp "
                  f"{WORK}/result.json > {WORK}/grade.txt 2>&1; echo $? > {WORK}/grade.code")
        code, _out, err = offline(io, script, extra=[("--ro-bind", ro, GRADE)], timeout=2400)
        found = read_json(os.path.join(io, "result.json"))
        if found is None:
            result = dict(result, deliverable=True, error=f"the check did not finish (exit {code}): "
                          + (h1.tail(os.path.join(io, "grade.txt")) or err[-200:]), grading_failed=True)
        else:
            result = found
        shutil.rmtree(os.path.join(io, "tmp"), ignore_errors=True)
        os.remove(os.path.join(io, "output.pptx"))
    shutil.rmtree(ro, ignore_errors=True)
    result["deliverable_sha256"] = sha
    return result


def idle_dir():
    return os.path.join(STATE, "idle")


def grade_idle(unit, work, out_dir):
    """The H1 class A grading: the src/ folder of the working copy on a fresh copy of the base, the hidden test
    alone, then the existing suite against the recorded baseline. Correct: every item passes and no regression."""
    base_cases = read_json(os.path.join(idle_dir(), "suite_baseline.json"))["cases"]
    io, fresh = os.path.join(out_dir, "io"), os.path.join(out_dir, "proj")
    os.makedirs(io)
    shutil.copytree(os.path.join(idle_dir(), "proj"), fresh, symlinks=True)
    shutil.rmtree(os.path.join(fresh, "src"))
    candidate = os.path.join(work, "src")
    if os.path.isdir(candidate) and not os.path.islink(candidate):
        shutil.copytree(candidate, os.path.join(fresh, "src"), symlinks=True, ignore=h1.only_plain)
    with open(os.path.join(io, "hidden.py"), "w", encoding="utf-8") as handle:
        handle.write(unit["hidden_test"])
    name = h1.hidden_name(unit)
    steps = [f"cd {IDLE_WORK} || exit 90", f"cp {GRADE}/hidden.py tests/{name} || exit 93",
             f"timeout -k 30 600 {h1.PYTEST} tests/{name} --junitxml={GRADE}/hidden.xml > {GRADE}/hidden.txt 2>&1",
             f"echo $? > {GRADE}/hidden.code", f"rm -f tests/{name}",
             f"timeout -k 30 1500 {h1.PYTEST} tests --junitxml={GRADE}/suite.xml > {GRADE}/suite.txt 2>&1",
             f"echo $? > {GRADE}/suite.code"]
    code, _out, err = offline(fresh, "\n".join(steps), io=io, workdir=IDLE_WORK, idle=True)
    shutil.rmtree(fresh, ignore_errors=True)
    hidden_exit, suite_exit = h1.number(os.path.join(io, "hidden.code")), h1.number(os.path.join(io, "suite.code"))
    cases, alien = h1.hidden_cases(unit, h1.junit(os.path.join(io, "hidden.xml")))
    frozen, functions = unit.get("nodes"), unit.get("functions") or sorted(cases)

    def good(fn):
        seen = cases.get(fn) or {}
        if not seen or any(status != "passed" for status in seen.values()):
            return False
        return frozen is None or sorted(seen) == frozen.get(fn)

    passed = {fn: good(fn) for fn in functions}
    items = unit.get("items") or {fn: [fn] for fn in functions}
    met = {key: bool(members) and all(passed.get(fn, False) for fn in members) for key, members in items.items()}
    current = h1.junit(os.path.join(io, "suite.xml"))
    regression, lost = None, []
    if current is not None:
        lost = sorted(node for node, status in base_cases.items() if status == "passed" and current.get(node) != "passed")
        regression = suite_exit != 0 or bool(lost)
    elif suite_exit is not None:
        regression = True
    error = ""
    if code or hidden_exit is None or suite_exit is None:
        error = f"grading script exit {code}, hidden {hidden_exit}, suite {suite_exit}: {err[-200:]}"
    score = (0.0 if regression else sum(met.values()) / len(met)) if met else None
    return {"error": error, "hidden_exit": hidden_exit, "suite_exit": suite_exit, "suite_regression": regression,
            "suite_lost": len(lost), "items": met, "passed": sum(met.values()), "n": len(met), "score": score,
            "alien": alien[:20], "pass": score == 1.0, "hidden_tail": h1.tail(os.path.join(io, "hidden.txt")),
            "suite_tail": h1.tail(os.path.join(io, "suite.txt"))}


# ---------------------------------------------------------------- budget of the claude cell

def budget_path():
    return os.path.join(STATE, "budget.json")


def ledger_path():
    return os.path.join(STATE, "ledger-claude.jsonl")


def budget():
    """(cap, decision, logical tokens spent before this state folder): the base, then every recorded raise."""
    base = read_json(budget_path())
    if base is None:
        raise SystemExit("no budget base in the state root; run `budget --spent-before N` first")
    cap, decision = int(base["cap"]), base["decision"]
    for entry in read_rows(os.path.join(STATE, "budget-raise.jsonl")):
        if not re.fullmatch(r"D\d+", str(entry.get("decision"))) or int(entry.get("cap") or 0) <= cap:
            raise SystemExit("budget-raise.jsonl has an entry that names no decision or does not raise the cap")
        cap, decision = int(entry["cap"]), entry["decision"]
    return cap, decision, int(base["spent_before"])


def stop_line():
    """The line a projected spend may not pass: 27M under the 30M cap, moved with a recorded raise."""
    return budget()[0] - (CAP - STOP_LINE)


def cell_spent():
    """Logical tokens of the claude cell: the spend before this state folder, every session that ended, and for a
    session that started and never ended the larger of its reserve and the usage left in its raw file."""
    before = budget()[2]
    started, ended = {}, {}
    for entry in read_rows(ledger_path()):
        (started if entry["event"] == "start" else ended)[entry["key"]] = entry
    total = before + sum(int(entry.get("tokens") or 0) for entry in ended.values())
    for key, entry in started.items():
        if key not in ended:
            raw = os.path.join(STATE, entry["raw"])
            seen = h1.claude_usage(open(raw, encoding="utf-8", errors="replace"))[0] if os.path.exists(raw) else 0
            total += max(int(entry.get("reserve") or 0), seen)
    return total


def budget_left():
    return budget()[0] - cell_spent()


def claude_gate(kind):
    """Why the next claude session of this kind may not start, or ''. The same test for every claude session,
    probes included: spent + RESERVE x the estimate must not pass the stop line."""
    spent, need = cell_spent(), estimate(kind)
    if spent + RESERVE * need > stop_line():
        return (f"budget: spent {spent:,}; the next {kind} session (about {need:,} x {RESERVE}) passes "
                f"{stop_line():,}")
    return ""


def cmd_budget(args):
    if args.raise_to is None:
        if os.path.exists(budget_path()):
            raise SystemExit("the budget base is written once")
        if args.spent_before is None or args.spent_before < 0:
            raise SystemExit("give --spent-before: logical tokens the claude cell used outside this state folder")
        write_json(budget_path(), {"cap": CAP, "decision": CAP_DECISION, "spent_before": args.spent_before,
                                   "written": now()})
    else:
        if not re.fullmatch(r"D\d+", args.decision or ""):
            raise SystemExit("a raise names the owner decision that allows it (--decision D<number>)")
        if args.raise_to <= budget()[0]:
            raise SystemExit("a raise must be larger than the current cap")
        append(os.path.join(STATE, "budget-raise.jsonl"), {"cap": args.raise_to, "decision": args.decision,
                                                           "written": now()})
    cap, decision, before = budget()
    print(json.dumps({"cap": cap, "decision": decision, "spent_before": before, "spent": cell_spent(),
                      "stop_line": stop_line()}, indent=1))
    return 0


def exclusive(name):
    """A lock of this state folder held until the process ends; a second holder is refused."""
    handle = open(os.path.join(STATE, name), "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit(f"another process holds {name} of this state folder")
    return handle


def claude_session(key, kind, call):
    """A claude session entered in the cell's ledger before it starts and after it ends."""
    append(ledger_path(), {"event": "start", "key": key, "raw": key, "reserve": estimate(kind), "time": now()})
    session = call()
    append(ledger_path(), {"event": "end", "key": key, "tokens": session.get("tokens_total") or 0, "time": now()})
    return session


# ---------------------------------------------------------------- disk (PLAN.md section 10)

def disk_figures():
    """Measured peak scratch use and kept size of one run (the largest so far over every tag and cell), or the
    first assumptions when nothing was measured."""
    peaks, kept = [], []
    for path in glob.glob(os.path.join(STATE, "attempts-*-*.jsonl")):
        for row in read_rows(path):
            peaks.append(int(row.get("scratch_bytes") or 0))
            kept.append(int(row.get("kept_bytes") or 0))
    frozen = ((read_json(os.path.join(STATE, "units_ppt.json")) or {}).get("disk") or {}).get(
        "peak_of_selected_tasks", 0)
    return {"peak_scratch_bytes": max(peaks + [frozen]) if any(peaks) or frozen else DISK_FIRST_PEAK,
            "kept_bytes": max(kept) if any(kept) else DISK_FIRST_KEPT, "measured_runs": sum(1 for p in peaks if p)}


def space_gate(runs_left):
    """Why the next run may not start for lack of disk space, or ''. Needed: the peak scratch use of the largest
    run measured so far times the runs that may be in flight, on the scratch disk; what the remaining runs will
    keep plus 15 GB, on the state disk; all of it together when both are one disk."""
    figures = disk_figures()
    scratch_need = figures["peak_scratch_bytes"] * CELLS_AT_ONCE
    state_need = figures["kept_bytes"] * max(1, runs_left) + DISK_SAFETY
    scratch_free, state_free = shutil.disk_usage(SCRATCH).free, shutil.disk_usage(STATE).free
    if os.stat(SCRATCH).st_dev == os.stat(STATE).st_dev:
        if state_free < scratch_need + state_need:
            return f"disk: {state_free:,} bytes free, {scratch_need + state_need:,} needed"
        return ""
    if scratch_free < scratch_need:
        return f"disk: {scratch_free:,} bytes free for scratch, {scratch_need:,} needed"
    if state_free < state_need:
        return f"disk: {state_free:,} bytes free for the state, {state_need:,} needed"
    return ""


# ---------------------------------------------------------------- one run

def task_dir(unit_id):
    return os.path.join(STATE, "tasks", unit_id)


def safe_id(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", str(value)):
        raise SystemExit(f"{value!r} is not usable as a name")
    return value


def live_dir(root):
    """The folder on the scratch disk that holds the working folder and the home of the run kept at `root`."""
    return os.path.join(SCRATCH, os.path.relpath(root, STATE))


class Peak(threading.Thread):
    """Largest size of a run's scratch folder while it runs, sampled every few seconds."""

    def __init__(self, folder, every=10):
        super().__init__(daemon=True)
        self.folder, self.every, self.peak, self.stop = folder, every, 0, threading.Event()

    def run(self):
        while not self.stop.wait(self.every):
            self.sample()

    def sample(self):
        if os.path.isdir(self.folder):
            self.peak = max(self.peak, tree_bytes(self.folder))

    def finish(self):
        self.stop.set()
        self.sample()
        return self.peak


def settle(live, root, keep_work=True):
    """Move what is kept of a finished run from scratch to the state and empty the scratch folder. Kept: the grade
    folder (deliverable, result, slide pictures), and the working folder when it is small; otherwise its listing."""
    grade = os.path.join(live, "grade")
    if os.path.isdir(grade):
        shutil.move(grade, os.path.join(root, "grade"))
    work = os.path.join(live, "work")
    listing = []
    if os.path.isdir(work):
        for base, dirs, names in os.walk(work):
            dirs[:] = sorted(d for d in dirs if d not in (".venv", ".git", "node_modules", "__pycache__"))
            for name in sorted(names):
                path = os.path.join(base, name)
                if not os.path.islink(path):
                    listing.append([os.path.relpath(path, work), os.path.getsize(path)])
        if keep_work and sum(size for _name, size in listing) <= KEEP_WORK_BYTES:
            shutil.copytree(work, os.path.join(root, "work"), symlinks=True,
                            ignore=shutil.ignore_patterns(".venv", ".git", "node_modules", "__pycache__"))
    shutil.rmtree(live, ignore_errors=True)
    return listing[:300]


def run_unit(cell, arm, unit, kind, attempt, tag, provenance=None):
    """One session of one unit in one arm, then the grade. Returns (row, reason it does not count or '')."""
    group = group_of(arm)
    root = os.path.join(STATE, "runs", tag, cell, safe_id(unit["id"]), arm, f"a{attempt}")
    if os.path.isdir(root):
        root += f"-{int(time.time())}"
    append(starts_path(tag, cell), dict(provenance or {}, event="start", tag=tag, cell=cell, kind=kind,
                                        unit=unit["id"], arm=arm, attempt=attempt,
                                        root=os.path.relpath(root, STATE), time=now()))
    row = {"cell": cell, "arm": arm, "group": group, "unit": unit["id"], "kind": kind, "attempt": attempt, "tag": tag,
           "started": now(), "flags": [], "root": os.path.relpath(root, STATE), "tokens_total": 0,
           "tokens_noncache": 0, "seconds": 0}
    live = live_dir(root)
    os.makedirs(live)
    peak = Peak(live)
    peak.start()
    try:
        reason = one_run(cell, group, unit, kind, root, live, row, tag)
    except OSError as error:
        if error.errno != errno.ENOSPC:
            raise
        reason = "no space left on a disk"
    row["scratch_bytes"] = peak.finish()
    try:
        row["work_files"] = settle(live, root, keep_work=kind == "answer")
    except OSError as error:
        if error.errno != errno.ENOSPC:
            raise
        reason = reason or "no space left on a disk"
        shutil.rmtree(live, ignore_errors=True)
    row["kept_bytes"] = tree_bytes(root) if os.path.isdir(root) else 0
    if reason:
        row["not_run"] = reason
    row["finished"] = now()
    return row, reason


def one_run(cell, group, unit, kind, root, live, row, tag):
    """The session and the grade of a run; fills the row and returns the reason it does not count or ''."""
    work, home, raw = os.path.join(live, "work"), os.path.join(live, "home"), os.path.join(root, "raw")
    os.makedirs(raw)
    fresh_home(home, cell)
    wanted = frozen_entry(cell, group)
    if kind == "answer":      # the task as stored must be the task that was verified
        row["task_tree_sha256"] = tree_digest(task_dir(unit["id"]))
        if row["task_tree_sha256"] != unit["task_sha256"]:
            raise SystemExit(f"{unit['id']}: the stored task is not the one that was verified")
    if kind == "idle":
        shutil.copytree(os.path.join(idle_dir(), "proj"), work, symlinks=True)
        prompt = h1.PROMPT.format(task=unit["sessions"][0])
    else:
        os.makedirs(work)
        shutil.copytree(os.path.join(task_dir(unit["id"]), "inputs"), os.path.join(work, "inputs"))
        prompt = PROMPT.format(task=unit["prompt"])

    def call():
        return run_session(cell, group, work, home, prompt, raw, "s1", idle=kind == "idle",
                           allow=budget_left() if cell == "claude" else None,
                           lists=wanted.get("startup_lists") if tag == "main" else None)

    if cell == "claude":
        if budget_left() <= 0:
            return "budget cap"
        session = claude_session(os.path.relpath(os.path.join(raw, "s1.jsonl"), STATE), kind, call)
    else:
        session = call()
    with open(os.path.join(raw, "s1.final.txt"), "w", encoding="utf-8") as handle:
        handle.write(session.pop("final") + "\n---\n" + session.pop("stderr_tail", ""))
    row["session"] = session
    row["tokens_total"], row["tokens_noncache"] = session.get("tokens_total") or 0, session.get("tokens_noncache") or 0
    row["seconds"], row["startup_tokens"] = session["seconds"], session.get("startup_tokens")
    reason = h1.not_run(session, cell, MODELS[cell])
    if not reason and shutil.disk_usage(SCRATCH).free < SCRATCH_FLOOR:
        reason = "no space left on the scratch disk when the session ended"
    if tag == "main" and (session["exit"] == STARTUP
                          or sorted(session.get("listed_skills") or []) != (wanted.get("listed_skills") or [])
                          or (cell == "claude" and session.get("startup_lists") != wanted.get("startup_lists"))):
        reason = f"{STARTUP} differ from the frozen ones of the group"
    if not reason and cell == "claude" and budget_left() < 0:
        reason = "budget cap"
    if not reason and session["net"]["allowed"] == {}:
        reason = "no model connection went through the proxy"
    if session["exit"] in ("timeout", "token ceiling"):
        row["flags"].append(f"session {session['exit']}")
    if session.get("over_ceiling"):
        row["flags"].append("over the token ceiling with its subagents")
    if reason:
        return reason
    if kind == "idle":
        code, text, _err = offline(work, "export GIT_OPTIONAL_LOCKS=0\ngit diff", workdir=IDLE_WORK, idle=True,
                                   timeout=300)
        with open(os.path.join(raw, "final.diff"), "w", encoding="utf-8") as handle:
            handle.write(text if code == 0 else "<git diff failed>\n")
    for _try in range(2):  # grading is mechanical; a second try only covers a failure of the grading step itself
        out = os.path.join(live, "grade")
        if os.path.isdir(out):
            shutil.rmtree(out)
        row["grade"] = (grade_idle(unit, work, out) if kind == "idle" else
                        grade_answer(task_dir(unit["id"]), work, out))
        failed = (row["grade"].get("grading_failed") or row["grade"].get("infra") or row["grade"].get("check_error")
                  or (kind == "idle" and (row["grade"]["error"] or row["grade"]["score"] is None)))
        if not failed or "no space" in str(row["grade"].get("infra")):
            break
    if failed:      # no verdict on the deliverable: the run does not count
        if "no space" in str(row["grade"].get("infra")):
            return "no space left on a disk"
        if row["grade"].get("check_error"):     # the task's own check broke on this deck: not the deck's failure
            return f"grading failed: the task's check raised {row['grade']['check_error']}"
        return f"grading failed: {row['grade'].get('infra') or row['grade'].get('error')}"
    row["passed"] = bool(row["grade"].get("pass"))
    return ""


def starts_path(tag, cell):
    return os.path.join(STATE, f"starts-{tag}-{cell}.jsonl")


def attempts_path(tag, cell):
    return os.path.join(STATE, f"attempts-{tag}-{cell}.jsonl")


def rows_path(tag, cell):
    return os.path.join(STATE, f"rows-{tag}-{cell}.jsonl")


def tried(tag, cell, unit_id, arm):
    """Every attempt of a unit in one arm under a tag: the finished ones, and for a run that was started and never
    finished a failed attempt 'interrupted'. So an attempt cannot be dropped by stopping the runner."""
    finished = [r for r in read_rows(attempts_path(tag, cell)) if r["unit"] == unit_id and r["arm"] == arm]
    roots = {r.get("root") for r in finished}
    lost = [dict(s, not_run="interrupted") for s in read_rows(starts_path(tag, cell))
            if s["unit"] == unit_id and s["arm"] == arm and s["root"] not in roots]
    return finished + lost


class rows_lock:
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
    with rows_lock(tag, cell):
        kept = {r.get("root") for r in read_rows(rows_path(tag, cell))}
        have = {(r["unit"], r["arm"]) for r in read_rows(rows_path(tag, cell))}
        for attempt in read_rows(attempts_path(tag, cell)):
            key = (attempt["unit"], attempt["arm"])
            if not attempt.get("not_run") and attempt.get("root") not in kept and key not in have:
                append(rows_path(tag, cell), attempt)
                have.add(key)
                print(f"recovered the counted attempt {attempt['root']}", flush=True)


def main_started():
    return any(read_rows(path) for pattern in ("starts-main-*.jsonl", "attempts-main-*.jsonl", "rows-main-*.jsonl")
               for path in glob.glob(os.path.join(STATE, pattern)))


def estimate(kind):
    """Logical tokens the next claude session of this kind is expected to cost: the largest counted main run of the
    kind so far, the first estimate otherwise."""
    seen = [r["tokens_total"] for r in read_rows(rows_path("main", "claude")) if r["kind"] == kind]
    return max(seen) if seen else ESTIMATE[kind]


def incomplete_path(tag, cell):
    return os.path.join(STATE, f"incomplete-{tag}-{cell}.jsonl")


def load_units():
    ppt = read_json(os.path.join(STATE, "units_ppt.json"))
    idle = read_json(os.path.join(STATE, "units_idle.json"))
    return (ppt or {}).get("units", []), (idle or {}).get("units", [])


def unit_digest(unit):
    return hashlib.sha256(json.dumps(unit, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def cmd_run(args):
    """Tag main: the frozen sequence of a cell, after the state is checked against FREEZE.json. Tag calibration:
    every verified candidate task once in the codex cell, arm N1. One runner per tag and cell. Rows are bound to
    the unit entry, the lock and the freeze file; a first counted result is kept and never replaced."""
    tag, cell = args.tag, args.cell
    lock_sha = check_lock()
    holder = exclusive(f"run-{tag}-{cell}.lock")
    claude = exclusive("claude.lock") if cell == "claude" else None
    runner = digest(os.path.abspath(__file__))
    freeze_digest = ""
    if tag == "main":
        path = os.path.join(HERE, "FREEZE.json")
        frozen, current = read_json(path), manifest()
        differ = sorted(k for k in set(frozen) | set(current) if frozen.get(k) != current.get(k))
        if differ:
            print(f"the state differs from FREEZE.json in: {', '.join(differ)}", flush=True)
            return 6
        freeze_digest = digest(path)
        ppt, idle = load_units()
        plan = [(arm, kind, unit) for arm, kind in SEQUENCE for unit in (ppt if kind == "answer" else idle)]
    elif tag == "calibration":
        if cell != "codex":
            raise SystemExit("tag calibration runs in the codex cell")
        if os.path.exists(os.path.join(STATE, "units_ppt.json")):
            raise SystemExit("the tasks are selected; the calibration is closed")
        plan = [("N1", "answer", unit) for unit in read_json(os.path.join(STATE, "candidates.json"))["units"]]
    else:
        raise SystemExit("tags: main, calibration")
    earlier = read_rows(rows_path(tag, cell)) + read_rows(attempts_path(tag, cell)) + read_rows(starts_path(tag, cell))
    if any(r.get("runner_sha256") != runner or r.get("lock_sha256") != lock_sha for r in earlier):
        raise SystemExit(f"runs of another runner or lock exist under tag {tag}; use a new state folder")
    entries = {unit["id"]: unit_digest(unit) for _arm, _kind, unit in plan}
    for r in earlier:
        if r["unit"] in entries and (r.get("unit_sha256") != entries[r["unit"]]
                                     or r.get("freeze_sha256") != freeze_digest):
            raise SystemExit(f"{r['unit']}: a run exists for another version of this unit or another FREEZE.json")
    recover(tag, cell)
    done = {(r["unit"], r["arm"]) for r in read_rows(rows_path(tag, cell))}
    dropped = {r["candidate"] for r in read_rows(incomplete_path(tag, cell))}
    for place, (arm, kind, unit) in enumerate(plan):
        group = group_of(arm)
        if group in dropped:
            continue
        if group in CANDIDATES and template(group).get("status") != "ready":
            append(incomplete_path(tag, cell), {"candidate": group, "reason": "the install template is not ready: "
                                                + str(template(group).get("status")), "time": now()})
            dropped.add(group)
            continue
        while (unit["id"], arm) not in done:
            before = tried(tag, cell, unit["id"], arm)
            failed = [r for r in before if r.get("not_run") and not any(word in r["not_run"] for word in EXEMPT)]
            restarts = [r for r in before if STARTUP in (r.get("not_run") or "")]
            if len(restarts) >= MAX_RESTARTS:
                failed = failed + restarts
            if len(failed) >= MAX_ATTEMPTS:
                print(f"{unit['id']}/{arm}: {len(failed)} attempts did not count", flush=True)
                if group not in CANDIDATES:
                    return 5
                append(incomplete_path(tag, cell), {"candidate": group, "time": now(), "reason":
                                                    f"{unit['id']}: {len(failed)} attempts did not count"})
                dropped.add(group)
                break
            short = space_gate(len(plan) - place)
            if short:
                print(short + "; not started", flush=True)
                return 8
            if cell == "claude":
                closed = claude_gate(kind)
                if closed:
                    print(closed + "; stopping in sequence", flush=True)
                    return 4
            provenance = {"unit_sha256": entries[unit["id"]], "runner_sha256": runner, "lock_sha256": lock_sha,
                          "check_sha256": digest(os.path.join(HERE, "ppt_check.py")), "freeze_sha256": freeze_digest}
            row, reason = run_unit(cell, arm, unit, kind, len(before) + 1, tag, provenance)
            row.update(provenance, model_asked=MODELS[cell])
            with rows_lock(tag, cell):
                if not reason and any(r["unit"] == unit["id"] and r["arm"] == arm
                                      for r in read_rows(rows_path(tag, cell))):
                    reason = row["not_run"] = "a counted row for this unit and arm already exists"
                append(attempts_path(tag, cell), row)
                if not reason:
                    append(rows_path(tag, cell), row)
            print(f"{cell} {unit['id']}/{arm} a{row['attempt']}: "
                  + (f"NOT RUN ({reason}), " if reason else f"{'pass' if row['passed'] else 'fail'}, ")
                  + f"{row['tokens_total']:,} tokens, {row['seconds']:.0f}s {row['flags'] or ''}", flush=True)
            if not reason:
                done.add((unit["id"], arm))
            elif "usage limit" in reason:
                return 3
            elif "budget cap" in reason:
                return 4
            elif "no space" in reason:
                return 8
    del holder, claude
    return 0


# ---------------------------------------------------------------- setup: tool copies, idle corpus, the lock

def source_problems(group, source):
    """A mount source must be a folder inside its template, named by a relative path, and no link in it may lead
    out of the template: then the template's digest covers everything that is mounted."""
    root = os.path.realpath(os.path.join(TEMPLATES, group))
    path = os.path.join(TEMPLATES, group, source)
    if os.path.isabs(source) or ".." in source.split("/"):
        return [f"mount source {source} is not a plain relative path"]
    if not os.path.isdir(path) or os.path.islink(path) or not within(path, root):
        return [f"mount source {source} is missing, a link, or outside the template"]
    for base, dirs, names in os.walk(path):
        for name in dirs + names:
            item = os.path.join(base, name)
            if os.path.islink(item) and not within(item, root):
                return [f"mount source {source} holds a link out of the template: {os.path.relpath(item, root)}"]
    return []


def template_problems():
    """What is wrong with the templates: more than MAX_UNITS units, no pin, a mount source that is not wholly inside
    its template, a mount outside the sandbox home, a candidate mount that touches anything shared (the common
    tools, the tool copies, the system folders, the working folder, the login and state files), or skill mounts
    that are not exactly the listed units."""
    problems = [f"common: {problem}" for source, _target in template("common").get("mounts", [])
                for problem in source_problems("common", source)]
    common = [target for _source, target in template("common").get("mounts", [])]
    for group in CANDIDATES:
        info = template(group)
        if info.get("status") != "ready":
            continue
        units = info.get("units", [])
        if not 1 <= len(units) <= MAX_UNITS:
            problems.append(f"{group}: {len(units)} units; 1 to {MAX_UNITS} allowed")
        if not info.get("pin"):
            problems.append(f"{group}: no version pin")
        targets = [target for _source, target in info.get("mounts", [])]
        for source, target in info.get("mounts", []):
            problems += [f"{group}: {problem}" for problem in source_problems(group, source)]
            if not target.startswith(HOME + "/") or ".." in target.split("/"):
                problems.append(f"{group}: mount target {target} is outside the sandbox home")
            for shared in common + SHOW + list(SYSTEM_DIRS) + [WORK, IDLE_WORK, GRADE, NET, "/tmp", "/dev", "/proc",
                                                               f"{HOME}/.claude/.credentials.json",
                                                               f"{HOME}/.codex/auth.json", f"{HOME}/.claude.json"]:
                if target == shared or target.startswith(shared + "/") or shared.startswith(target + "/"):
                    problems.append(f"{group}: mount target {target} touches {shared}")
        for root in (f"{HOME}/.claude/skills", f"{HOME}/.agents/skills"):
            listed = sorted(t[len(root) + 1:] for t in targets if t.startswith(root + "/"))
            if listed != sorted(units):
                problems.append(f"{group}: mounts under {root} are {listed}, the units are {sorted(units)}")
    return problems


def templates_facts():
    """Content digest, status, pin, units and mount targets of the shared tools and of every candidate template."""
    facts = {}
    for name in ("common",) + CANDIDATES:
        info = template(name)
        facts[name] = {"status": info.get("status"), "units": info.get("units", []), "pin": info.get("pin"),
                       "mounts": [target for _source, target in info.get("mounts", [])],
                       "content_sha256": tree_digest(os.path.join(TEMPLATES, name))
                       if os.path.isdir(os.path.join(TEMPLATES, name)) else None}
    return facts


def locked_now(tools=None):
    """What `setup` locks: the plan, the brief and the programs, the H1 runner, the templates and the tool copies."""
    return {"files": {name: digest(os.path.join(HERE, name)) for name in LOCKED_FILES},
            "h1_run_sha256": digest(H1_FILE), "templates": templates_facts(),
            "tools": tools if tools is not None else
            [{"index": i, "content_sha256": tree_digest(snapshot(i))} for i in range(len(SHOW))]}


def check_lock():
    """Refuse to go on when anything locked by `setup` has changed: the plan, the brief, the programs, every
    template and the tool copies. Returns the digest of the lock. Every command checks all of it."""
    recorded = read_json(os.path.join(STATE, "setup.json"))
    if recorded is None:
        raise SystemExit("run `setup` first")
    lock = recorded["lock"]
    problems = template_problems()
    if problems:
        raise SystemExit("templates: " + "; ".join(problems))
    current = locked_now()
    for key in lock:
        if lock[key] != current[key]:
            detail = ""
            if isinstance(lock[key], dict):
                detail = ": " + ", ".join(sorted(k for k in set(lock[key]) | set(current[key])
                                                 if lock[key].get(k) != current[key].get(k)))
            raise SystemExit(f"changed since setup locked it: {key}{detail}. Use a new state folder.")
    return hashlib.sha256(json.dumps(lock, sort_keys=True).encode()).hexdigest()


def cmd_setup(_args):
    """Copy the CAP_RO folders, prepare the idle corpus with its suite baseline (two runs that must agree) and the
    two idle units, and write the lock: digests of the plan, the brief, the programs, every template and the tool
    copies. The candidates (versions, units, install content) are fixed here, before any task is written."""
    out_path = os.path.join(STATE, "setup.json")
    if os.path.exists(out_path):
        raise SystemExit("setup.json exists; use a fresh CAP_STATE to set up again")
    problems = template_problems()
    if problems:
        raise SystemExit("templates: " + "; ".join(problems))
    for index, shown in enumerate(SHOW):
        if not os.path.isdir(snapshot(index)):
            shutil.copytree(shown, snapshot(index), symlinks=True)
    tools = [{"index": i, "content_sha256": tree_digest(snapshot(i))} for i in range(len(SHOW))]
    os.makedirs(idle_dir())
    proj = os.path.join(idle_dir(), "proj")
    shutil.copytree(BASE, proj, symlinks=True)
    probe = os.path.join(SCRATCH, "baseline", "check")   # git reads a working copy only where the user owns it
    shutil.rmtree(probe, ignore_errors=True)
    shutil.copytree(proj, probe, symlinks=True)
    code, text, err = offline(probe, "export GIT_OPTIONAL_LOCKS=0\ngit rev-parse HEAD && git status --porcelain | wc -l",
                              workdir=IDLE_WORK, idle=True, timeout=300)
    shutil.rmtree(probe, ignore_errors=True)
    if code or text.split()[:2] != [h1.BASE_COMMIT, "0"]:
        raise SystemExit(f"the idle corpus is not a clean checkout of the H1 base commit: {text} {err[-200:]}")
    runs = []
    for index in (1, 2):
        io = os.path.join(SCRATCH, "baseline", str(index))
        shutil.rmtree(io, ignore_errors=True)
        os.makedirs(io)
        fresh = os.path.join(io, "proj")
        shutil.copytree(proj, fresh, symlinks=True)
        offline(fresh, f"cd {IDLE_WORK} || exit 90\ntimeout 1500 {h1.PYTEST} tests --junitxml={GRADE}/suite.xml "
                       f"> {GRADE}/suite.txt 2>&1\necho $? > {GRADE}/suite.code", io=io, workdir=IDLE_WORK, idle=True)
        runs.append((h1.number(os.path.join(io, "suite.code")), h1.junit(os.path.join(io, "suite.xml"))))
        shutil.rmtree(io, ignore_errors=True)
    if any(code != 0 or cases is None for code, cases in runs) or runs[0][1] != runs[1][1]:
        raise SystemExit(f"the existing suite is not stable on the base: exits {[code for code, _ in runs]}")
    if any(status != "passed" for status in runs[0][1].values()):
        raise SystemExit("the existing suite on the base has cases that do not pass")
    write_json(os.path.join(idle_dir(), "suite_baseline.json"), {"exit": 0, "cases": runs[0][1]})
    frozen_a = read_json(os.path.join(HERE, "..", "H1", "FREEZE.json"))["units"]["A"]
    if digest(IDLE_UNITS) != frozen_a:
        raise SystemExit("CAP_IDLE_UNITS is not the class A unit file that H1 froze")
    bank = read_json(IDLE_UNITS)
    units = [u for u in bank["units"] if u["id"] in IDLE_IDS]
    if [u["id"] for u in units] != list(IDLE_IDS):
        raise SystemExit("the class A unit file does not hold the idle units in order")
    write_json(os.path.join(STATE, "units_idle.json"), {"source_sha256": digest(IDLE_UNITS), "units": units})
    out = {"idle": {"base_commit": h1.BASE_COMMIT, "proj_sha256": tree_digest(proj), "suite_cases": len(runs[0][1]),
                    "suite_baseline_sha256": digest(os.path.join(idle_dir(), "suite_baseline.json")),
                    "units_sha256": digest(os.path.join(STATE, "units_idle.json")),
                    "h1_units_A_sha256": digest(IDLE_UNITS)},
           "lock": locked_now(tools), "written": now()}
    write_json(out_path, out)
    print(json.dumps(out, indent=1))
    return 0


# ---------------------------------------------------------------- warm CLI state of the claude cell

def cmd_warm(_args):
    """Write the CLI state file that every claude home starts with: two one-line sessions of group N in one home,
    then that home's .claude.json. It holds what the CLI caches about the account (which decides two of the
    commands it lists), nothing of a candidate and nothing of a task. Written once per state folder."""
    check_lock()
    if os.path.exists(warm_path()):
        raise SystemExit("the warm CLI state is written once")
    holder = exclusive("claude.lock")
    root = os.path.join(STATE, "runs", "probe", "claude", "warm", str(int(time.time())))
    live = live_dir(root)
    work, home = os.path.join(live, "work"), os.path.join(live, "home")
    os.makedirs(work)
    fresh_home(home, "claude", warm=False)
    seen = []
    for index in (1, 2):
        raw = os.path.join(root, f"raw{index}")
        os.makedirs(raw)
        closed = claude_gate("probe")
        if closed:
            raise SystemExit(closed)
        session = claude_session(
            os.path.relpath(os.path.join(raw, "s1.jsonl"), STATE), "probe",
            lambda: run_session("claude", "N", work, home, "Reply with the single word OK and nothing else. "
                                "Do not use any tool.", raw, "s1", allow=budget_left()))
        reason = h1.not_run(session, "claude", MODELS["claude"])
        if reason:
            raise SystemExit(f"warm-up session {index} did not run: {reason}")
        seen.append({"startup_tokens": session.get("startup_tokens"), "tokens_total": session.get("tokens_total"),
                     "lists": session.get("startup_lists")})
    os.makedirs(os.path.dirname(warm_path()), exist_ok=True)
    shutil.copyfile(os.path.join(home, ".claude.json"), warm_path())
    keys = sorted(read_json(warm_path()))
    write_json(os.path.join(STATE, "warm", "record.json"), {"sha256": digest(warm_path()), "keys": keys,
                                                           "sessions": seen, "time": now()})
    shutil.rmtree(live, ignore_errors=True)
    print(json.dumps({"sha256": digest(warm_path()), "keys": keys,
                      "startup_tokens": [s["startup_tokens"] for s in seen]}, indent=1))
    del holder
    return 0


# ---------------------------------------------------------------- probe

NET_PROBE = r"""
fail=0
try() { # name, command: the command must fail
  if timeout 25 bash -c "$2" >/dev/null 2>&1; then echo "REACHED $1"; fail=1; else echo "blocked $1"; fi
}
try curl-npm 'curl -fsS https://registry.npmjs.org/left-pad'
try curl-pypi 'curl -fsS https://pypi.org/simple/pip/'
try curl-github 'curl -fsS https://github.com/'
try curl-noproxy 'curl -fsS --noproxy "*" https://github.com/'
try curl-http 'curl -fsS http://example.com/'
try curl-ip 'curl -fsS --noproxy "*" --connect-timeout 8 https://1.1.1.1/'
try python-pypi 'python3 -c "import urllib.request; urllib.request.urlopen(\"https://pypi.org/simple/pip/\", timeout=15)"'
try python-direct 'python3 -c "import socket; socket.create_connection((\"1.1.1.1\", 443), timeout=8)"'
try pip-download 'python3 -m pip download --no-deps -d /tmp/pipdl left-pad==0.0.3'
try npm-view 'npm view left-pad version'
try node-fetch 'node -e "fetch(\"https://registry.npmjs.org/left-pad\").then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"'
try git-remote 'git ls-remote https://github.com/git/git HEAD'
try dns 'getent hosts github.com'
try host-socket 'ls /run/* /var/run/* 2>/dev/null | grep -q .'
exit $fail
"""
# What a session can see of the machine, as a listing: the top of the file system, /home, the home folder two
# levels deep, and every socket outside /tmp.
LOOK = (r"echo '# /'; ls -A / | tr '\n' ' '; echo; echo '# /home'; ls -A /home | tr '\n' ' '; echo; echo '# home'; "
        r"find " + HOME + r" -maxdepth 2 -not -path '*/site-packages/*' -not -path '*/work/*' | sort | head -60; "
        r"echo '# sockets'; find / -xdev -type s -not -path '/proc/*' -not -path '/tmp/*' 2>/dev/null | head; "
        r"echo '# env'; env | cut -d= -f1 | sort | tr '\n' ' '")


def probe_config(group):
    """Digest of what a probe of this group ran under: the launch configuration, the proxy program, the shared and
    the group's template and the tool copies, all as `setup` locked them."""
    lock = read_json(os.path.join(STATE, "setup.json"))["lock"]
    parts = {"launch": launch_config(), "cap_net": lock["files"]["cap_net.py"], "tools": lock["tools"],
             "warm": digest(warm_path()) if os.path.exists(warm_path()) else None,
             "templates": {name: lock["templates"][name] for name in ["common"] + ([group] if group in CANDIDATES
                                                                                   else [])}}
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def cmd_probe(args):
    """Before any counted run: inside the session sandbox of every group, downloads from npm, PyPI and GitHub must
    fail by every route tried, no host socket may be visible, and a one-line model session must work. Records what
    each group's session lists at startup (skills, tools, billing source), what it can see of the machine, what the
    proxy saw, and the digest of the configuration it ran under."""
    cell = args.cell
    check_lock()
    out_path = os.path.join(STATE, f"probe-{cell}.json")
    if main_started():
        raise SystemExit("main runs have started; the probe record is fixed")
    holder = exclusive(f"probe-{cell}.lock")
    claude = exclusive("claude.lock") if cell == "claude" else None
    out = read_json(out_path, {"cell": cell, "groups": {}})
    for group in args.groups.split(","):
        if group in CANDIDATES and template(group).get("status") != "ready":
            out["groups"][group] = {"skipped": f"template not ready: {template(group).get('status')}"}
            continue
        root = os.path.join(STATE, "runs", "probe", cell, group, str(int(time.time())))
        live = live_dir(root)
        work, home, raw = os.path.join(live, "work"), os.path.join(live, "home"), os.path.join(root, "raw")
        for folder in (work, raw):
            os.makedirs(folder)
        fresh_home(home, cell)
        proxy = Proxy(cell, os.path.join(raw, "netprobe.net.jsonl"))
        Ctx.group, Ctx.workdir, Ctx.netdir, Ctx.idle = group, WORK, proxy.folder, False
        try:
            done = subprocess.run(sandbox(work, home, None, ["/bin/bash", "-c", NET_PROBE]), env=environment(),
                                  capture_output=True, text=True, timeout=900)
            look = subprocess.run(sandbox(work, home, None, ["/bin/bash", "-c", LOOK]), env=environment(),
                                  capture_output=True, text=True, timeout=300)
        finally:
            proxy.close()
        entry = {"net_probe_exit": done.returncode, "net_probe": done.stdout.strip().splitlines(),
                 "net_probe_proxy": proxy.summary(), "inside": look.stdout.strip().splitlines(),
                 "config_sha256": probe_config(group)}
        prompt = "Reply with the single word OK and nothing else. Do not use any tool."

        def call():
            return run_session(cell, group, work, home, prompt, raw, "s1",
                               allow=budget_left() if cell == "claude" else None)

        if cell == "claude":
            closed = claude_gate("probe")
            if closed:
                raise SystemExit(closed)
            session = claude_session(os.path.relpath(os.path.join(raw, "s1.jsonl"), STATE), "probe", call)
        else:
            session = call()
        reason = h1.not_run(session, cell, MODELS[cell])
        entry.update({key: session.get(key) for key in (
            "exit", "api_key_source", "provider", "model", "root_models", "listed_skills", "listed_tools",
            "listed_agents", "mcp_servers", "permission_mode", "version", "tokens_total", "startup_tokens", "net",
            "mounts", "path", "context", "startup_lists")})
        entry["final"], entry["not_run"] = session.get("final", "")[:80], reason
        entry["time"] = now()
        if entry["listed_skills"] is not None:
            entry["listed_skills"] = sorted(entry["listed_skills"])
        if group in out["groups"]:  # an earlier probe of the group is kept, never dropped
            out.setdefault("history", []).append(dict(out["groups"][group], group=group))
        out["groups"][group] = entry
        write_json(out_path, out)
        shutil.rmtree(live, ignore_errors=True)
        print(f"{cell} {group}: net probe exit {done.returncode}, session {'NOT RUN ' + reason if reason else 'ok'}, "
              f"{session.get('tokens_total')} tokens, skills {entry['listed_skills']}", flush=True)
    del holder, claude
    return 0


# ---------------------------------------------------------------- authoring and verification (no claude)

def authors_path():
    return os.path.join(STATE, "authors.jsonl")


def packet_files():
    """What an author receives: the brief and the check library. Nothing of any candidate."""
    return {"BRIEF.md": os.path.join(HERE, "AUTHOR_BRIEF_PPT.md"), "ppt_check.py": os.path.join(HERE, "ppt_check.py")}


def author_out(name):
    return os.path.join(STATE, "authors", name, "out")


def cmd_author(args):
    """One blind author: a fresh Codex session with the brief and the check library, the N tools, no candidate. The
    start entry records the lock, which fixes the candidates' versions, units and install content before any task
    exists, and the packet, which is the same for every author."""
    name = safe_id(args.name)
    lock_sha = check_lock()
    holder = exclusive("author.lock")
    counted = [r for r in read_rows(authors_path()) if r["event"] == "start"]
    if any(r["name"] == name for r in counted):
        raise SystemExit(f"author {name} has already been started; an author runs once")
    if len(counted) >= MAX_AUTHORS:
        raise SystemExit(f"{MAX_AUTHORS} authors have run; report to the owner instead of asking another")
    if os.path.exists(os.path.join(STATE, "units_ppt.json")):
        raise SystemExit("the tasks are selected; no further author")
    if counted:     # a supplement: only after every earlier author is verified and calibrated, and too few qualify
        short = read_json(os.path.join(STATE, "select-short.json"))
        if not short or short["authors"] != [r["name"] for r in counted]:
            raise SystemExit("a further author runs only after `select` found too few tasks among all earlier ones")
    root = os.path.join(STATE, "authors", name)
    live = live_dir(root)
    work, home, raw = os.path.join(live, "work"), os.path.join(live, "home"), os.path.join(root, "raw")
    for folder in (work, raw):
        os.makedirs(folder)
    fresh_home(home, "codex")
    packet = {}
    for target, source in packet_files().items():
        shutil.copyfile(source, os.path.join(work, target))
        packet[target] = digest(source)
    append(authors_path(), {"event": "start", "name": name, "packet": packet, "time": now(), "lock_sha256": lock_sha,
                            "candidates": {g: template(g).get("units") for g in CANDIDATES}})
    prompt = "Read BRIEF.md in the current directory and do what it says."
    session = run_session("codex", "N", work, home, prompt, raw, "s1", seconds=args.hours * 3600)
    reason = h1.not_run(session, "codex", MODELS["codex"])
    made = os.path.join(work, "_out")
    tasks = sorted(os.listdir(made)) if os.path.isdir(made) else []
    if os.path.isdir(made):
        shutil.copytree(made, author_out(name), symlinks=False,
                        ignore=shutil.ignore_patterns("__pycache__", "lo-profile"))
    append(authors_path(), {"event": "end", "name": name, "time": now(), "not_run": reason,
                            "tokens_total": session.get("tokens_total"), "seconds": session.get("seconds"),
                            "final": session.get("final", "")[:200], "net": session.get("net"),
                            "out_sha256": tree_digest(author_out(name)) if tasks else None, "tasks": tasks})
    shutil.rmtree(live, ignore_errors=True)
    print(f"author {name}: {'NOT RUN ' + reason if reason else 'done'}, {session.get('tokens_total')} tokens, "
          f"{session.get('seconds')}s, tasks {tasks}")
    del holder
    return 1 if reason else 0


KINDS = ("overflow", "cut", "covered", "duplicate", "rotated", "white", "picture")
# Decks that no author made. A task's check must answer for each of them (and fail it) without raising: in a run, a
# check that raises gives no verdict and stops the cell.
STRESS = r"""
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches
def deck(name, wide=True):
    prs = Presentation()
    if wide:
        prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    return prs
prs = deck("one"); prs.slides.add_slide(prs.slide_layouts[6]); prs.save("stress-one-empty-slide.pptx")
prs = deck("many")
for number in range(14):
    slide = prs.slides.add_slide(prs.slide_layouts[5]); slide.shapes.title.text = "x%d" % number
prs.save("stress-fourteen-titles.pptx")
prs = deck("mix", wide=False)
for number in range(3):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    table = slide.shapes.add_table(1, 1, Inches(0.5), Inches(0.5), Inches(3), Inches(0.5)).table
    table.cell(0, 0).text = "a"
    data = CategoryChartData(); data.categories = ["a"]; data.add_series("s", (1,))
    slide.shapes.add_chart(XL_CHART_TYPE.PIE, Inches(4), Inches(0.5), Inches(4), Inches(3), data)
    data = CategoryChartData(); data.categories = []; 
    slide.shapes.add_chart(XL_CHART_TYPE.LINE, Inches(4), Inches(4), Inches(4), Inches(3), data)
prs.save("stress-tables-and-charts.pptx")
"""


def grade_deck(task, deck, out_dir):
    """Grade one of an author's decks; `deck` None stands for an empty delivery."""
    work = os.path.join(out_dir, "work")
    os.makedirs(work)
    if deck:
        shutil.copyfile(deck, os.path.join(work, "output.pptx"))
    result = grade_answer(task, work, os.path.join(out_dir, "grade"))
    shutil.rmtree(out_dir, ignore_errors=True)
    rules = sorted({f["rule"] for f in result.get("failures", [])} | ({"task"} if result.get("task_failures") else set())
                   | ({"error"} if result.get("error") else set()))
    return {"pass": bool(result.get("pass")), "rules": rules, "error": result.get("error", ""),
            "check_error": result.get("check_error", ""), "task_failures": result.get("task_failures", [])[:5],
            "grading_failed": bool(result.get("grading_failed") or result.get("infra"))}


def verify_task(folder, out_dir):
    """Mechanical verification of one authored task (PLAN.md section 4). Returns (valid, report)."""
    report = {"problems": [], "decks": {}}
    need = ["prompt.md", "check.py", "expect.json", "inputs", "decks"]
    missing = [name for name in need if not os.path.exists(os.path.join(folder, name))]
    if missing:
        report["problems"].append(f"missing {', '.join(missing)}")
        return False, report
    decks = sorted(name for name in os.listdir(os.path.join(folder, "decks")) if name.endswith(".pptx"))
    good = [n for n in decks if n == "reference.pptx" or n.startswith("alt-")]
    bad = [n for n in decks if n.startswith("bad-")]
    if "reference.pptx" not in decks or len(good) < 3:
        report["problems"].append("needs reference.pptx and at least two alt-*.pptx")
    for kind in KINDS:
        if not any(n.startswith(f"bad-{kind}") for n in bad):
            report["problems"].append(f"no counterexample bad-{kind}*.pptx")
    if sum(1 for n in bad if n.startswith("bad-x-")) < 2:
        report["problems"].append("needs at least two task-specific counterexamples bad-x-*.pptx")
    try:
        expect = read_json(os.path.join(folder, "expect.json")) or {}
    except ValueError:
        expect = {}
        report["problems"].append("expect.json is not JSON")
    inputs = sorted(os.listdir(os.path.join(folder, "inputs")))
    if not inputs:
        report["problems"].append("no input material")
    if "output.pptx" not in open(os.path.join(folder, "prompt.md"), encoding="utf-8").read():
        report["problems"].append("the prompt does not name output.pptx")
    if report["problems"]:
        return False, report
    jobs = {name: os.path.join(folder, "decks", name) for name in decks}
    stress = os.path.join(out_dir, "stress")
    os.makedirs(stress)
    with open(os.path.join(stress, "make.py"), "w", encoding="utf-8") as handle:
        handle.write(STRESS)
    offline(stress, f"cd {WORK} && python3 make.py", timeout=600)
    for name in sorted(n for n in os.listdir(stress) if n.endswith(".pptx")):
        jobs[f"<{name[:-5]}>"] = os.path.join(stress, name)
    if len([n for n in jobs if n.startswith("<stress")]) != 3:
        report["problems"].append("the stress decks could not be made")
        return False, report
    jobs["<empty>"] = None
    for name in inputs:
        path = os.path.join(folder, "inputs", name)
        if os.path.isfile(path):
            jobs[f"<input {name}>"] = path
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {name: pool.submit(grade_deck, folder, path, os.path.join(out_dir, re.sub(r"\W", "_", name)))
                   for name, path in jobs.items()}
        report["decks"] = {name: future.result() for name, future in futures.items()}
    for name, result in report["decks"].items():
        if result["grading_failed"] or result["check_error"]:
            report["problems"].append(f"{name}: the check itself failed ({result['error'] or result['check_error']})")
        elif name in good and not result["pass"]:
            report["problems"].append(f"{name}: must pass, broke {result['rules']}")
        elif name not in good and result["pass"]:
            report["problems"].append(f"{name}: must fail and passed")
        elif name in bad:
            wanted = expect.get(name)
            if not isinstance(wanted, list) or not wanted:
                report["problems"].append(f"{name}: expect.json names no rule for it")
            elif not set(wanted) & set(result["rules"]):
                report["problems"].append(f"{name}: failed on {result['rules']}, not on any of {wanted}")
    return not report["problems"], report


def cmd_verify(args):
    """Verify every task of one author. Valid tasks are copied to the state's task store under <author>-<task>;
    invalid ones are dropped, never repaired. The report is bound to the lock and to the digest of what it checked."""
    name = safe_id(args.author)
    lock_sha = check_lock()
    ended = [r for r in read_rows(authors_path()) if r["event"] == "end" and r["name"] == name]
    started = [r for r in read_rows(authors_path()) if r["event"] == "start" and r["name"] == name]
    if not ended or ended[-1].get("not_run"):
        raise SystemExit(f"author {name} has no finished run")
    if started[-1].get("packet") != {name: digest(path) for name, path in packet_files().items()}:
        raise SystemExit("the author received another brief or check library than the present ones")
    out = author_out(name)
    if not os.path.isdir(out) or tree_digest(out) != ended[-1]["out_sha256"]:
        raise SystemExit("the author's output is missing or changed since the session ended")
    report_path = os.path.join(STATE, f"verified-{name}.json")
    if os.path.exists(report_path):
        raise SystemExit("this author's tasks are already verified; a verification is done once")
    report = {"author": name, "lock_sha256": lock_sha, "out_sha256": ended[-1]["out_sha256"], "tasks": {},
              "time": now()}
    names = sorted(n for n in os.listdir(out) if os.path.isdir(os.path.join(out, n)))
    for task in names[:AUTHOR_TASKS]:
        folder = os.path.join(out, task)
        valid, found = verify_task(folder, os.path.join(SCRATCH, "verify", name, safe_id(task)))
        unit_id = f"{name}-{task}"
        found.update(valid=valid, task_sha256=tree_digest(folder))
        if valid:
            store = task_dir(unit_id)
            if os.path.exists(store):
                raise SystemExit(f"{unit_id} is already in the task store")
            shutil.copytree(folder, store)
        report["tasks"][unit_id] = found
        print(f"{unit_id}: {'valid' if valid else 'DROPPED: ' + '; '.join(found['problems'])[:300]}", flush=True)
    report["ignored"] = names[AUTHOR_TASKS:]
    write_json(report_path, report)
    write_candidates()
    return 0


def cmd_regrade(args):
    """Amendment 2. A calibration session that ran in an earlier state folder is not run again: that would be a
    second draw. The deliverable it left, kept bit for bit, is graded again with the present check, and the row is
    entered here with what the session recorded then and where it came from. Only for tasks whose stored content
    and unit entry are the ones that session ran."""
    lock_sha = check_lock()
    holder = exclusive("run-calibration-codex.lock")
    if os.path.exists(os.path.join(STATE, "units_ppt.json")):
        raise SystemExit("the tasks are selected; the calibration is closed")
    runner = digest(os.path.abspath(__file__))
    source_rows = os.path.join(args.source, "rows-calibration-codex.jsonl")
    listed = read_rows(source_rows)
    earlier = {r["unit"]: r for r in listed}
    if len(earlier) != len(listed) or any(r.get("arm") != "N1" or r.get("not_run") for r in listed):
        raise SystemExit("the source holds two rows for one task, or a row that is not a counted N1 run")
    if any(read_rows(path) for path in (starts_path("calibration", "codex"), attempts_path("calibration", "codex"),
                                        rows_path("calibration", "codex"))):
        raise SystemExit("this state folder already has calibration records; grading again is done once, on an "
                         "empty calibration ledger, so that runs and regrades cannot be mixed for one task")
    units = read_json(os.path.join(STATE, "candidates.json"))["units"]
    if set(earlier) - {u["id"] for u in units}:
        raise SystemExit("the source holds calibration rows for tasks that are not candidates here")
    write_json(os.path.join(STATE, "regrade-source.json"), {"rows_sha256": digest(source_rows), "units": sorted(earlier),
                                                           "time": now()})
    for unit in units:
        old = earlier.get(unit["id"])
        if old is None:
            continue
        kept = os.path.join(args.source, old["root"], "grade", "deliverable", "output.pptx")
        tree = tree_digest(task_dir(unit["id"]))
        if old.get("unit_sha256") != unit_digest(unit) or old.get("task_tree_sha256") != tree:
            raise SystemExit(f"{unit['id']}: the earlier session ran another version of this task")
        if tree != unit["task_sha256"]:
            raise SystemExit(f"{unit['id']}: the stored task is not the one that was verified")
        if not os.path.isfile(kept) or digest(kept) != (old.get("grade") or {}).get("deliverable_sha256"):
            raise SystemExit(f"{unit['id']}: the kept deliverable is missing or changed")
        root = os.path.join(STATE, "runs", "calibration", "codex", safe_id(unit["id"]), "N1", "a1")
        provenance = {"unit_sha256": unit_digest(unit), "runner_sha256": runner, "lock_sha256": lock_sha,
                      "check_sha256": digest(os.path.join(HERE, "ppt_check.py")), "freeze_sha256": ""}
        origin = {"runner_sha256": old.get("runner_sha256"), "lock_sha256": old.get("lock_sha256"),
                  "check_sha256": old.get("check_sha256"), "root": old["root"], "passed_then": old.get("passed")}
        append(starts_path("calibration", "codex"), dict(provenance, event="start", tag="calibration", cell="codex",
                                                         kind="answer", unit=unit["id"], arm="N1", attempt=1,
                                                         root=os.path.relpath(root, STATE), time=now(),
                                                         regraded_from=origin))
        live = live_dir(root)
        os.makedirs(os.path.join(live, "work"))
        shutil.copyfile(kept, os.path.join(live, "work", "output.pptx"))
        grade = grade_answer(task_dir(unit["id"]), os.path.join(live, "work"), os.path.join(live, "grade"))
        if grade.get("grading_failed") or grade.get("infra") or grade.get("check_error"):
            raise SystemExit(f"{unit['id']}: grading again failed: {grade.get('infra') or grade.get('error')}")
        os.makedirs(root)
        settle(live, root, keep_work=False)
        row = dict(old, provenance, grade=grade, passed=bool(grade.get("pass")), root=os.path.relpath(root, STATE),
                   task_tree_sha256=tree, regraded_from=origin, regraded=now())
        with rows_lock("calibration", "codex"):
            append(attempts_path("calibration", "codex"), row)
            append(rows_path("calibration", "codex"), row)
        print(f"{unit['id']}: graded again: {'pass' if row['passed'] else 'fail'} (then: "
              f"{'pass' if old.get('passed') else 'fail'})", flush=True)
    del holder
    return 0


def write_candidates():
    """candidates.json: every valid task of every author, authors in the order they ran, tasks in each author's
    order. This is what the calibration runs."""
    units = []
    present = {name: digest(path) for name, path in packet_files().items()}
    for start in [r for r in read_rows(authors_path()) if r["event"] == "start"]:
        if start["packet"] != present:
            # Amendment 3: an author who received another brief or check library than the present ones is void.
            # It wrote and tried its tasks against that other library, so they are not candidates here; it still
            # counts among the MAX_AUTHORS.
            continue
        report = read_json(os.path.join(STATE, f"verified-{start['name']}.json"))
        ended = [r for r in read_rows(authors_path()) if r["event"] == "end" and r["name"] == start["name"]]
        if report is None and not (ended and (ended[-1].get("not_run") or not ended[-1].get("tasks"))):
            raise SystemExit(f"author {start['name']} is not verified yet; no author is skipped")
        for unit_id, found in sorted((report or {}).get("tasks", {}).items()):
            if found["valid"]:
                prompt = open(os.path.join(task_dir(unit_id), "prompt.md"), encoding="utf-8").read().strip()
                units.append({"id": unit_id, "author": start["name"], "prompt": prompt,
                              "task_sha256": found["task_sha256"]})
    write_json(os.path.join(STATE, "candidates.json"), {"units": units})
    return units


def cmd_select(_args):
    """Take the first TASKS candidate tasks, in order, that the codex cell did not pass in its one calibration run
    (a pass is the ceiling). Every calibration row must carry this lock (so the same checks and thresholds), this
    runner and the unit entry it ran; a candidate with no counted calibration row, or with two, stops the
    selection. With fewer than TASKS, exit 7: ask a new author (at most MAX_AUTHORS in all) or report to the owner."""
    lock_sha = check_lock()
    if main_started():
        raise SystemExit("main runs have started; the unit file is fixed")
    if os.path.exists(os.path.join(STATE, "units_ppt.json")):
        raise SystemExit("the tasks are already selected")
    authors = [r for r in read_rows(authors_path()) if r["event"] == "start"]
    present = {name: digest(path) for name, path in packet_files().items()}
    void = [r["name"] for r in authors if r["packet"] != present]
    stored = (read_json(os.path.join(STATE, "candidates.json")) or {}).get("units", [])
    units = write_candidates()      # built again from every author's record: no author and no task is skipped
    if units != stored:
        raise SystemExit("candidates.json is not what the authors' verification reports give")
    rows = read_rows(rows_path("calibration", "codex"))
    runner = digest(os.path.abspath(__file__))
    chosen, notes = [], {}
    for unit in units:
        mine = [r for r in rows if r["unit"] == unit["id"] and r["arm"] == "N1"]
        if (len(mine) != 1 or mine[0].get("unit_sha256") != unit_digest(unit) or mine[0].get("lock_sha256") != lock_sha
                or mine[0].get("runner_sha256") != runner):
            raise SystemExit(f"{unit['id']}: needs exactly one counted calibration row of this unit, lock and runner")
        if not (tree_digest(task_dir(unit["id"])) == unit["task_sha256"] == mine[0].get("task_tree_sha256")):
            raise SystemExit(f"{unit['id']}: the stored task, the verified task and the calibrated task differ")
        if not mine[0].get("scratch_bytes"):
            raise SystemExit(f"{unit['id']}: its calibration run has no measured scratch peak")
        notes[unit["id"]] = "ceiling" if mine[0]["passed"] else "not passed"
        if not mine[0]["passed"] and len(chosen) < TASKS:
            chosen.append(unit)
    out = {"units": chosen, "calibration": notes, "candidates": [u["id"] for u in units],
           "authors": [r["name"] for r in authors], "void_authors": void, "lock_sha256": lock_sha,
           "candidates_sha256": digest(os.path.join(STATE, "candidates.json")),
           "calibration_rows_sha256": digest(rows_path("calibration", "codex"))
           if os.path.exists(rows_path("calibration", "codex")) else None,
           "disk": {key: value for key, value in disk_figures().items() if key != "measured_runs"}}
    print(json.dumps({"chosen": [u["id"] for u in chosen], "calibration": notes}, indent=1))
    if len(chosen) < TASKS:
        print(f"only {len(chosen)} of {TASKS} tasks qualify")
        write_json(os.path.join(STATE, "select-short.json"), {"authors": out["authors"], "qualify": len(chosen),
                                                              "calibration": notes, "time": now()})
        return 7
    # PLAN.md section 10: the peak scratch use measured on the largest selected task is part of what is frozen
    out["disk"] = dict(out["disk"], peak_of_selected_tasks=max(
        int(r["scratch_bytes"]) for r in rows if r["unit"] in {u["id"] for u in chosen}))
    write_json(os.path.join(STATE, "units_ppt.json"), out)
    return 0


# ---------------------------------------------------------------- what is frozen before the main runs

def scrub(text):
    real = os.path.expanduser("~")
    swaps = [(BIN, "$CAP_BIN"), (STATE, "$CAP_STATE"), (SCRATCH, "$CAP_SCRATCH"), (SNAP, "$CAP_SNAP"),
             (TEMPLATES, "$CAP_TEMPLATES"), (BASE, "$CAP_BASE"), (real, "~")]
    swaps += [(path, f"$CAP_RO[{i}]") for i, path in enumerate(SHOW)]
    for path, name in sorted((s for s in swaps if s[0]), key=lambda s: len(s[0]), reverse=True):
        text = text.replace(path, name)
    if os.path.basename(real) and os.path.basename(real) in text:
        raise SystemExit("launch: a local name is left in the launch configuration")
    return text


def launch_config():
    """How every session and every grading step is started, with local paths replaced by setting names."""
    run = os.path.join(SCRATCH, "runs", "<run>")
    cells = {}
    saved = (Ctx.group, Ctx.workdir, Ctx.netdir, Ctx.idle)
    for cell in ("claude", "codex"):
        Ctx.group, Ctx.workdir, Ctx.netdir, Ctx.idle = "N", WORK, None, False
        argv = claude_argv("<prompt>", MODELS[cell]) if cell == "claude" else codex_argv(MODELS[cell])
        copy = next((snapshot(i) + argv[0][len(s):] for i, s in enumerate(SHOW)
                     if argv[0] == s or argv[0].startswith(s + os.sep)), argv[0])
        cells[cell] = {"model": MODELS[cell], "cli_version": h1.tool_version([copy, "--version"]),
                       "cli_sha256": digest(os.path.realpath(copy)) if os.path.isfile(os.path.realpath(copy)) else None,
                       "argv": argv, "prompt_on": "argv" if cell == "claude" else "stdin", "allow": ALLOW[cell],
                       "billing_source_required": "none" if cell == "claude" else "chatgpt",
                       "sandbox_of_group_N": sandbox(os.path.join(run, "work"), os.path.join(run, "home"), cell,
                                                     ["<argv>"], prepare=False)}
    config = {"cells": cells, "session_environment": environment(), "grading_environment": environment(tools=False),
              "system_dirs": list(SYSTEM_DIRS), "prompt": PROMPT, "idle_prompt": h1.PROMPT, "sequence": SEQUENCE,
              "idle_ids": list(IDLE_IDS),
              "limits": {"session_seconds": SESSION_SECONDS, "token_ceiling": CEILING, "max_attempts": MAX_ATTEMPTS,
                         "exempt": list(EXEMPT), "cap": CAP, "stop_line": STOP_LINE, "reserve": RESERVE,
                         "first_estimates": ESTIMATE, "idle_ratio": IDLE_RATIO, "tasks": TASKS,
                         "author_tasks": AUTHOR_TASKS, "max_authors": MAX_AUTHORS, "max_units": MAX_UNITS,
                         "codex_slots": CODEX_SLOTS, "cells_at_once": CELLS_AT_ONCE, "disk_safety": DISK_SAFETY,
                         "scratch_floor": SCRATCH_FLOOR, "max_restarts": MAX_RESTARTS},
              "disallowed_tools": DISALLOWED.split(","), "bwrap_version": h1.tool_version(["bwrap", "--version"]),
              "local_settings_sha256": hashlib.sha256(json.dumps([SHOW, BIN]).encode()).hexdigest()}
    Ctx.group, Ctx.workdir, Ctx.netdir, Ctx.idle = saved
    return json.loads(scrub(json.dumps(config)))


def system_tools():
    out = {}
    for name in SYSTEM_TOOLS:
        found = shutil.which(name, path="/usr/bin:/bin")
        real = os.path.realpath(found) if found else None
        flag = "-v" if name in ("pdftotext", "pdftoppm", "pdftohtml") else "--version"
        out[name] = {"sha256": digest(real) if real else None,
                     "version": h1.tool_version([real, flag]) if real else "missing"}
    return out


def manifest():
    """Everything a main run depends on, as digests. Raises when anything `setup` locked has changed."""
    lock_sha = check_lock()
    recorded = read_json(os.path.join(STATE, "setup.json"))
    idle = dict(recorded["idle"], proj_sha256=tree_digest(os.path.join(idle_dir(), "proj")),
                suite_baseline_sha256=digest(os.path.join(idle_dir(), "suite_baseline.json")),
                units_sha256=digest(os.path.join(STATE, "units_idle.json")))
    if idle != recorded["idle"]:
        raise SystemExit("the idle corpus is no longer what setup.json recorded")
    ppt, _idle = load_units()
    tasks = {unit["id"]: tree_digest(task_dir(unit["id"])) for unit in ppt}
    for unit in ppt:
        if tasks[unit["id"]] != unit["task_sha256"]:
            raise SystemExit(f"{unit['id']}: the stored task is no longer what was verified")
    base = read_json(budget_path())
    probes = {}
    for cell in ("claude", "codex"):
        groups = (read_json(os.path.join(STATE, f"probe-{cell}.json"), {}).get("groups") or {})
        probes[cell] = {group: dict({key: entry.get(key) for key in (
            "listed_skills", "listed_tools", "api_key_source", "version", "net_probe_exit", "not_run", "skipped",
            "config_sha256", "startup_lists")}, config_current=probe_config(group))
                        for group, entry in groups.items()}
    thresholds = load_module("ppt_check_for_manifest", os.path.join(HERE, "ppt_check.py")).THRESHOLDS
    selection = {key: value for key, value in (read_json(os.path.join(STATE, "units_ppt.json")) or {}).items()
                 if key != "units"}
    out = {"lock_sha256": lock_sha, "lock": recorded["lock"], "idle": idle,
           "warm_sha256": digest(warm_path()) if os.path.exists(warm_path()) else None,
           "units_ppt_sha256": digest(os.path.join(STATE, "units_ppt.json")) if ppt else None, "tasks": tasks,
           "selection": selection,
           "budget": {key: base[key] for key in ("cap", "decision", "spent_before")} if base else None,
           "probes": probes, "thresholds": thresholds, "system_tools": system_tools(), "launch": launch_config()}
    return json.loads(json.dumps(out, sort_keys=True))


def cmd_manifest(args):
    current = manifest()
    if args.write:
        if main_started():
            raise SystemExit("main runs have started; the freeze file is not rewritten")
        problems = template_problems()
        if len(current["tasks"]) != TASKS:
            problems.append(f"{len(current['tasks'])} tasks selected, {TASKS} needed")
        if not current["budget"]:
            problems.append("no budget base")
        if not current["warm_sha256"]:
            problems.append("no warm CLI state")
        if not (current["selection"].get("disk") or {}).get("peak_of_selected_tasks"):
            problems.append("no scratch peak measured on the selected tasks")
        for cell, groups in current["probes"].items():
            base = (groups.get("N") or {}).get("listed_skills")
            if base is None:
                problems.append(f"{cell}: no probe of group N")
                continue
            for group in ("N",) + CANDIDATES:
                entry = groups.get(group) or {}
                if group in CANDIDATES and template(group).get("status") != "ready":
                    continue
                listed = entry.get("listed_skills")
                if listed is None or entry.get("not_run") or entry.get("net_probe_exit") != 0:
                    problems.append(f"{cell}/{group}: no clean probe")
                    continue
                if entry.get("config_sha256") != entry.get("config_current"):
                    problems.append(f"{cell}/{group}: probed under another configuration than the one to freeze")
                units = template(group).get("units", []) if group in CANDIDATES else []
                if sorted(set(listed) - set(base)) != sorted(units) or set(base) - set(listed):
                    problems.append(f"{cell}/{group}: lists {sorted(set(listed) - set(base))} beyond N, the frozen "
                                    f"units are {units}")
                if entry.get("listed_tools") != (groups.get("N") or {}).get("listed_tools"):
                    problems.append(f"{cell}/{group}: lists other tools than N")
                if cell == "claude":
                    mine = (entry.get("startup_lists") or {}).get("commands")
                    theirs = ((groups.get("N") or {}).get("startup_lists") or {}).get("commands")
                    if mine is None or theirs is None or sorted(set(mine) - set(theirs)) != sorted(units) \
                            or set(theirs) - set(mine):
                        problems.append(f"{cell}/{group}: the commands listed at startup differ from N by more "
                                        f"than the frozen units")
        if problems:
            raise SystemExit("not frozen: " + "; ".join(problems))
        write_json(args.out, current)
        print(os.path.basename(args.out), digest(args.out))
    else:
        print(json.dumps(current, indent=1, sort_keys=True))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup")
    sub.add_parser("warm")
    money = sub.add_parser("budget")
    money.add_argument("--spent-before", type=int)
    money.add_argument("--raise-to", type=int)
    money.add_argument("--decision")
    probe = sub.add_parser("probe")
    probe.add_argument("--cell", required=True, choices=("claude", "codex"))
    probe.add_argument("--groups", default="N,P1,P2,P3")
    author = sub.add_parser("author")
    author.add_argument("--name", required=True)
    author.add_argument("--hours", type=int, default=4)
    verify = sub.add_parser("verify")
    verify.add_argument("--author", required=True)
    sub.add_parser("select")
    again = sub.add_parser("regrade")
    again.add_argument("--source", required=True, help="the earlier state folder whose calibration sessions are kept")
    run = sub.add_parser("run")
    run.add_argument("--cell", required=True, choices=("claude", "codex"))
    run.add_argument("--tag", default="main")
    record = sub.add_parser("manifest")
    record.add_argument("--write", action="store_true")
    record.add_argument("--out", default=os.path.join(HERE, "FREEZE.json"))
    args = parser.parse_args()
    for name, value in (("CAP_STATE", STATE), ("CAP_SCRATCH", SCRATCH), ("CAP_SNAP", SNAP),
                        ("CAP_TEMPLATES", TEMPLATES), ("CAP_BASE", BASE), ("CAP_IDLE_UNITS", IDLE_UNITS),
                        ("CAP_RO", SHOW), ("CAP_BIN", BIN)):
        if not value:
            raise SystemExit(f"set {name}")
    guard_paths()
    os.makedirs(os.path.join(SCRATCH, "net"), exist_ok=True)
    os.makedirs(STATE, exist_ok=True)
    return {"setup": cmd_setup, "warm": cmd_warm, "budget": cmd_budget, "probe": cmd_probe, "author": cmd_author, "verify": cmd_verify,
            "select": cmd_select, "regrade": cmd_regrade, "run": cmd_run, "manifest": cmd_manifest}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
