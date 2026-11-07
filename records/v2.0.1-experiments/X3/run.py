"""X3: do agents pick the right working mode and start the right review on their own?

  python3 run.py setup  --scratch S --oaw200 DIR --oaw201 DIR   build the three arm repos (zero tokens)
  python3 run.py verify --scratch S                             expected modes per scenario (zero tokens)
  python3 run.py run    --scratch S --claude CLI [--budget N]   the paid runs, in the registered order
  python3 run.py grade  --scratch S                             mechanical grading -> S/rows.json

Fixture: make_fixture.py (same folder). OAW 2.0.0 = claude/oaw-2 332c585; 2.0.1 = claude/oaw-2 HEAD at run time.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
PY = "/usr/bin/python3"
GIT_ID = ["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid"]

MODELS = [("haiku", "claude-haiku-5-5"), ("opus", "claude-opus-5-5"), ("sonnet", "claude-sonnet-5-5")]
ARMS = ["0", "A", "B"]
BASE_ORDER = ["L1", "S1", "D1", "L2", "S2", "D2"]
EXPECTED = {"L1": "light", "L2": "light", "S1": "standard", "S2": "standard", "D1": "deep", "D2": "deep"}
REQUESTS = {
    "L1": 'Fix the typo "recieve" in the docstring of `parse_amount` in ledger/money.py.',
    "L2": ('`slugify` in ledger/text.py leaves hyphens at the ends: `slugify(" Hello, World! ")` returns '
           '"-hello-world-". Make it strip leading and trailing hyphens, and add a test case for it.'),
    "S1": ("Rename `get_conn` to `open_connection` across the whole project: the definition in ledger/db.py, "
           "every caller, the tests and the README. Don't keep the old name as an alias."),
    "S2": ("ledger/reports.py has grown too big. Split it into a `ledger/reports/` package with one module per "
           "report family (monthly and yearly, balances, budgets, payees, weekdays) plus one module for the "
           "table and CSV rendering helpers. Keep `from ledger.reports import ...` working for every function "
           "that exists today, delete the old reports.py, and make sure the tests still pass."),
    "D1": ("Add a GitHub Actions workflow that runs the test suite on every push and pull request, "
           "on Python 3.10 and 3.12."),
    "D2": ('Transactions need an optional category (for example "groceries" or "rent"). Add it to the database '
           "with a new migration, let `add_transaction` take a `category` argument and return it from "
           "`list_transactions`, and add a test."),
}
TOOLS = ["Read", "Edit", "Write", "Glob", "Grep", "Bash", "Skill"]
MAX_TURNS, TIMEOUT, EFFORT = 30, 900, "high"
DEFAULT_ESTIMATE = 500_000
B_REMOVED = [
    "Use the skills enabled in this project's recipe. EGM runs only as the design review of deep work; its switch "
    "is `python3 scripts/oaw_mode.py egm`.\n",
    "Work light by default: no extra review. Before a change, use the `oaw-review` skill or run "
    "`python3 scripts/oaw_mode.py suggest --paths <files you plan to change>`;\n",
    "after it, run `python3 scripts/oaw_mode.py suggest` (add `--range BASE..HEAD` for committed work or a pull "
    "request). Follow the steps it prints.\n",
]


def sh(args, cwd, check=True):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=check)


# ------------------------------------------------------------------------------------------------ setup

def setup(scratch: Path, oaw200: Path, oaw201: Path):
    arms = scratch / "arms"
    shutil.rmtree(arms, ignore_errors=True)
    for arm in ARMS:
        repo = arms / arm
        repo.mkdir(parents=True)
        sh([PY, str(HERE / "make_fixture.py"), str(repo)], cwd=scratch)
        sh(["git", "init", "-q", "-b", "main"], repo)
        sh(["git", *GIT_ID, "add", "-A"], repo)
        sh(["git", *GIT_ID, "commit", "-qm", "ledger 0.4.0"], repo)
        source = oaw200 if arm == "0" else oaw201
        sh([PY, str(source / "scripts/oaw.py"), "init", "--target", str(repo), "--host", "claude"], scratch)
        if arm == "B":
            policy = repo / "AGENTS.md"
            text = policy.read_text()
            assert all(line in text for line in B_REMOVED), "2.0.1 AGENTS.md changed; update B_REMOVED"
            text = text.replace(B_REMOVED[0], "Use the skills enabled in this project's recipe.\n")
            text = text.replace(B_REMOVED[1], "").replace(B_REMOVED[2], "")
            policy.write_text(text)
        if arm in ("A", "B"):
            (repo / ".oaw/settings.json").write_text(json.dumps({"review": {"dry_run": True}}, indent=2) + "\n")
        sh(["git", *GIT_ID, "add", "-A"], repo)
        sh(["git", *GIT_ID, "commit", "-qm", "Install OAW"], repo)
        assert sh(["git", "status", "--porcelain"], repo).stdout == ""
    print("arms ready:", ", ".join(ARMS))


# ------------------------------------------------------------------------------------------------ order

def run_order():
    """Model blocks (haiku, opus, sonnet); inside a block, scenario triples with the arm order rotated."""
    order = []
    for b, (short, model) in enumerate(MODELS):
        scenarios = BASE_ORDER[2 * b:] + BASE_ORDER[:2 * b]
        for k, scenario in enumerate(scenarios):
            r = (k + b) % 3
            arms = ARMS[r:] + ARMS[:r]
            order.append([(short, model, scenario, arm) for arm in arms])
    return order


def run_id(short, scenario, arm):
    return f"{short}-{scenario}-{arm}"


# ------------------------------------------------------------------------------------------------ run

def child_env():
    # No inherited ANTHROPIC_* or CLAUDE* variables (subscription login only); no claude/codex on PATH.
    return {"HOME": os.environ["HOME"], "USER": os.environ.get("USER", ""), "LOGNAME": os.environ.get("USER", ""),
            "SHELL": "/bin/bash", "LANG": "C.UTF-8", "TERM": "dumb", "PATH": "/usr/local/bin:/usr/bin:/bin"}


def usage_of(events):
    """Logical tokens: the result event's cumulative usage, else the sum over distinct assistant messages."""
    keys = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    result = next((e for e in events if e.get("type") == "result"), None)
    if result and result.get("usage"):
        u = result["usage"]
    else:
        per = {}
        for e in events:
            if e.get("type") == "assistant":
                per[e["message"].get("id")] = e["message"].get("usage", {})
        u = {k: sum(int(m.get(k) or 0) for m in per.values()) for k in keys}
    logical = sum(int(u.get(k) or 0) for k in keys)
    uncached = logical - int(u.get("cache_read_input_tokens") or 0)
    return logical, uncached


def read_events(path: Path):
    events = []
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    return events


def one_run(scratch: Path, claude: str, short, model, scenario, arm):
    rid = run_id(short, scenario, arm)
    folder = scratch / "runs" / rid
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    repo = folder / "repo"
    shutil.copytree(scratch / "arms" / arm, repo, symlinks=True)
    argv = [claude, "-p", REQUESTS[scenario], "--model", model, "--effort", EFFORT,
            "--output-format", "stream-json", "--verbose", "--no-session-persistence",
            "--permission-mode", "acceptEdits", "--tools", *TOOLS, "--allowedTools", "Bash",
            "--setting-sources", "project", "--strict-mcp-config", "--max-turns", str(MAX_TURNS)]
    start = time.time()
    timed_out = False
    with open(folder / "transcript.jsonl", "w") as out, open(folder / "stderr.txt", "w") as err:
        proc = subprocess.Popen(argv, cwd=repo, env=child_env(), stdout=out, stderr=err, stdin=subprocess.DEVNULL)
        try:
            proc.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            proc.wait()
    seconds = round(time.time() - start, 1)
    events = read_events(folder / "transcript.jsonl")
    logical, uncached = usage_of(events)
    meta = {"id": rid, "model": model, "scenario": scenario, "arm": arm, "seconds": seconds,
            "timed_out": timed_out, "returncode": proc.returncode, "tokens": logical, "tokens_uncached": uncached,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (folder / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def not_run(meta, events):
    """Zero tokens or cut by a usage limit: the run does not count and is resumed."""
    if meta["tokens"] == 0:
        return "zero tokens"
    result = next((e for e in events if e.get("type") == "result"), {})
    if not result.get("is_error") or result.get("subtype") == "error_max_turns":
        return None
    text = " ".join(str(result.get(k, "")) for k in ("result", "errors", "api_error_status"))
    if re.search(r"usage limit|rate.?limit|limit reached|quota|overloaded|\b429\b", text, re.I):
        return "usage limit"
    return None


def run_all(scratch: Path, claude: str, budget: int, spent_before: int, default_estimate: int = DEFAULT_ESTIMATE,
            sequential: bool = False, only_model: str = ""):
    ledger_path = scratch / "spend.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {
        "probes": spent_before, "runs": {}, "void": []}
    spent = lambda: ledger["probes"] + sum(m["tokens"] for m in ledger["runs"].values()) + sum(  # noqa: E731
        v["tokens"] for v in ledger["void"])
    for triple in run_order():
        todo = [t for t in triple if run_id(t[0], t[2], t[3]) not in ledger["runs"] and (not only_model or t[0] == only_model)]
        if not todo:
            continue
        estimates = []
        for short, model, scenario, arm in todo:
            seen = [m["tokens"] for m in ledger["runs"].values() if m["scenario"] == scenario]
            estimates.append(max(seen) if seen else default_estimate)
        if sequential:
            # Deviation 1 (see RESULT.md): one run at a time, each checked against the cap just before it starts.
            seen = [m["tokens"] for m in ledger["runs"].values() if m["scenario"] == todo[0][2]]
            estimate = max(seen) if seen else default_estimate
            if spent() + estimate > budget:
                print(f"STOP before {run_id(todo[0][0], todo[0][2], todo[0][3])}: spent {spent():,} + estimate "
                      f"{estimate:,} > budget {budget:,}", flush=True)
                break
            todo = todo[:1]
        elif spent() + sum(estimates) > budget:
            print(f"STOP before {[run_id(t[0], t[2], t[3]) for t in todo]}: spent {spent():,} + estimate "
                  f"{sum(estimates):,} > budget {budget:,}", flush=True)
            break
        with ThreadPoolExecutor(max_workers=len(todo)) as pool:
            futures = [pool.submit(one_run, scratch, claude, *t) for t in todo]
            metas = [f.result() for f in futures]
        for meta in metas:
            events = read_events(scratch / "runs" / meta["id"] / "transcript.jsonl")
            init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
            meta["apiKeySource"] = init.get("apiKeySource")
            why = not_run(meta, events)
            if why or meta["apiKeySource"] != "none":
                ledger["void"].append({**meta, "why": why or f"apiKeySource {meta['apiKeySource']}"})
                print("VOID", meta["id"], why or meta["apiKeySource"], f"tokens {meta['tokens']:,}", flush=True)
                if why == "usage limit":
                    ledger_path.write_text(json.dumps(ledger, indent=1))
                    print("usage limit: stopping; rerun later to resume", flush=True)
                    return
                continue
            ledger["runs"][meta["id"]] = meta
            print(f"{meta['id']}: {meta['tokens']:,} tokens, {meta['seconds']}s (spent {spent():,})", flush=True)
        ledger_path.write_text(json.dumps(ledger, indent=1))
        if sequential and any(run_id(t[0], t[2], t[3]) not in ledger["runs"] for t in triple):
            return run_all(scratch, claude, budget, spent_before, default_estimate, sequential, only_model)
    ledger_path.write_text(json.dumps(ledger, indent=1))
    print(f"done: {len(ledger['runs'])} runs, spent {spent():,}", flush=True)


# ------------------------------------------------------------------------------------------------ grade

DOC_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ".adoc"}
PLAN_PATH = re.compile(r"^docs/(plans|designs|adrs?|rfcs?)/|plan|design", re.I)
CODEISH = re.compile(r"\.(py|sql|ya?ml|toml|cfg|ini|json)\b|\bledger/|\btests/|\bmigrations/|\.github/")
REDIRECT = re.compile(r"(?<![0-9&<>])>{1,2}\s*([^\s;&|<>]+)")
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?")
MODE_RE = (re.compile(r'"mode":\s*"(light|standard|deep)"'), re.compile(r"^mode:\s*(light|standard|deep)\b", re.M))
REVIEW_SKILLS = {"code-review", "security-review", "review", "egm-review", "egm-review-loop"}


def is_doc(rel):
    return rel.split("/", 1)[0] == "docs" or PurePosixPath(rel).suffix.lower() in DOC_SUFFIXES


def is_code(rel):
    return not is_doc(rel) and not rel.startswith((".oaw/", ".git/"))


def is_plan(rel):
    return is_doc(rel) and rel.lower().endswith(".md") and bool(PLAN_PATH.search(rel))


def strip_heredocs(cmd):
    """The command lines without heredoc bodies, and the bodies."""
    lines, kept, bodies, end = cmd.split("\n"), [], [], None
    for line in lines:
        if end is not None:
            if line.strip() == end:
                end = None
            else:
                bodies.append(line)
            continue
        kept.append(line)
        m = HEREDOC.search(line)
        if m:
            end = m.group(1)
    return "\n".join(kept), "\n".join(bodies)


def bash_write(cmd, repo):
    """(writes, writes_code, plan_targets) for a Bash command, by fixed patterns (approximate).
    Redirect targets outside the project (/dev/null, other temp files) do not count."""
    head, body = strip_heredocs(cmd)
    targets = [rel_path(repo, t) for t in REDIRECT.findall(head) if not t.startswith("&")]
    targets = [t for t in targets if t]
    plan_targets = [t for t in targets if is_plan(t)]
    code_targets = [t for t in targets if is_code(t)]
    inplace = re.search(r"\bsed\b[^|;&\n]*\s-i|\bperl\b[^|;&\n]*\s-\w*i\b|\btee\b", head)
    moves = re.search(r"(^|[;&|(]\s*|\s)(git\s+)?(mv|rm|cp)\s", head)
    git_restore = re.search(r"\bgit\s+(checkout|restore|stash|reset|apply)\b", head)
    py_write = re.search(r"\bpython3?\b", head) and re.search(r"write_text\(|\.write\(|open\([^)]*['\"][wa]", body + head)
    writes_code = bool(code_targets) or bool(git_restore) or bool(
        (inplace or moves) and CODEISH.search(head)) or bool(py_write and CODEISH.search(body + head))
    writes = writes_code or bool(targets) or bool(inplace or moves or py_write)
    return writes, writes_code, plan_targets


def result_text(block):
    content = block.get("content")
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return content or ""


def returned_mode(text):
    for pattern in MODE_RE:
        m = pattern.search(text)
        if m:
            return m.group(1)
    return None


def rel_path(repo, raw):
    """A project-relative path, or None when raw points outside the project."""
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        rel = PurePosixPath(raw).as_posix()
        while rel.startswith("./"):
            rel = rel[2:]
        return None if rel.startswith("../") else rel
    try:
        return p.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        try:
            return p.relative_to(repo).as_posix()
        except ValueError:
            return None


def final_changes(repo):
    """Files that differ from the installed state (HEAD~0 of the arm), committed or not, untracked included."""
    base = sh(["git", "rev-list", "--max-parents=0", "--all"], repo).stdout.split()
    install = sh(["git", "log", "--format=%H", "--grep=^Install OAW$"], repo).stdout.split()
    ref = install[-1] if install else base[0]
    changed = sh(["git", "diff", "--name-only", ref], repo).stdout.split()
    untracked = sh(["git", "ls-files", "--others", "--exclude-standard"], repo).stdout.split()
    committed = sh(["git", "rev-list", "--count", f"{ref}..HEAD"], repo).stdout.strip()
    return sorted(set(changed) | set(untracked)), int(committed or 0)


def grade_one(folder: Path):
    meta = json.loads((folder / "meta.json").read_text())
    repo = folder / "repo"
    events = read_events(folder / "transcript.jsonl")
    calls, results = [], {}
    final_text, served = "", set()
    for e in events:
        if e.get("type") == "assistant":
            served.add(e["message"].get("model"))
            for block in e["message"].get("content", []):
                if block.get("type") == "tool_use":
                    calls.append(block)
                elif block.get("type") == "text":
                    final_text = block.get("text", "")
        elif e.get("type") == "user" and isinstance(e["message"].get("content"), list):
            for block in e["message"]["content"]:
                if block.get("type") == "tool_result":
                    results[block.get("tool_use_id")] = result_text(block)
    result = next((e for e in events if e.get("type") == "result"), {})
    if result.get("result"):
        final_text = result["result"]

    code_edits, plan_writes, checks, skills, reviews, bash_writes, edited = [], [], [], [], [], [], set()
    oaw_settings_touched = False
    for i, call in enumerate(calls):
        name, args = call.get("name"), call.get("input") or {}
        out = results.get(call.get("id"), "")
        if name in ("Edit", "Write", "NotebookEdit"):
            rel = rel_path(repo, args.get("file_path") or args.get("notebook_path") or "")
            if rel is None:
                continue
            edited.add(rel)
            if rel.startswith(".oaw/"):
                oaw_settings_touched = True
            if is_code(rel):
                code_edits.append((i, rel))
            elif is_plan(rel):
                plan_writes.append((i, rel))
        elif name == "Skill":
            skill = str(args.get("skill") or args.get("name") or "")
            skills.append((i, skill))
            if skill.split(":")[-1] in REVIEW_SKILLS:
                reviews.append((i, "skill " + skill))
        elif name == "Bash":
            cmd = str(args.get("command") or "")
            for seg in re.split(r"&&|\|\||;|\n", cmd):
                if re.search(r"oaw_mode\.py\b.*\bsuggest\b", seg):
                    kind = "paths" if "--paths" in seg else ("range" if "--range" in seg else "tree")
                    checks.append({"i": i, "kind": kind, "mode": returned_mode(out)})
                    break
            if re.search(r"\bcodex\b[^|;&\n]*\breview\b|\bclaude\s+(-p|--print)\b", cmd):
                reviews.append((i, "bash " + cmd[:80]))
            writes, writes_code, plan_targets = bash_write(cmd, repo)
            if writes_code:
                code_edits.append((i, "bash"))
                bash_writes.append(cmd[:120])
            for t in plan_targets:
                plan_writes.append((i, t))
            if ".oaw/settings.json" in cmd and writes:
                oaw_settings_touched = True

    changed, commits = final_changes(repo)
    changed_code = [p for p in changed if is_code(p)]
    unattributed = [p for p in changed_code if p not in edited] if not bash_writes else []
    first_edit = min((i for i, _ in code_edits), default=None)
    last_edit = max((i for i, _ in code_edits), default=None)
    oaw_skill = [i for i, s in skills if s.split(":")[-1] == "oaw-review"]
    before = (lambda i: first_edit is None or i < first_edit)
    check_before = any(before(c["i"]) for c in checks) or any(before(i) for i in oaw_skill)
    pre = [c for c in checks if before(c["i"])]
    post = [c for c in checks if last_edit is not None and c["i"] > last_edit]
    ended_normally = result.get("subtype") == "success" and not meta.get("timed_out")
    planned_first = any(before(i) for i, _ in plan_writes)
    stopped = (not code_edits and ended_normally and (any(c["mode"] == "deep" for c in checks)
                                                      or re.search(r"design review|\bplan\b", final_text, re.I)))
    review_after = [r for r in reviews if last_edit is not None and r[0] > last_edit]
    post_flags = [c for c in post if c["mode"] in ("standard", "deep")]
    # Dry run: a pre-edit check that already said standard or deep, and a final message that names the review.
    pre_flag_reported = any(c["mode"] in ("standard", "deep") for c in pre) and bool(
        re.search(r"review", final_text, re.I))
    if planned_first or stopped:
        acted = "deep"
    elif code_edits and (review_after or post_flags or pre_flag_reported):
        acted = "standard"
    elif code_edits:
        acted = "light"
    else:
        acted = "none"
    expected = EXPECTED[meta["scenario"]]
    tests = sh([PY, "-m", "unittest", "discover", "-s", "tests", "-t", "."], repo, check=False)
    model_usage = (result.get("modelUsage") or {})
    thinking = sum(int(v.get("thinkingTokens") or 0) for v in model_usage.values())
    return {
        "id": meta["id"], "model": meta["model"], "scenario": meta["scenario"], "expected": expected,
        "arm": meta["arm"], "correct": acted == expected, "acted_mode": acted,
        "check_before_first_edit": check_before,
        "pre_edit_mode": pre[-1]["mode"] if pre else None, "pre_edit_check_kind": pre[-1]["kind"] if pre else None,
        "post_edit_mode": post[-1]["mode"] if post else None,
        "mode_checks": len(checks), "oaw_review_skill": bool(oaw_skill),
        "skills": [s for _, s in skills], "plan_doc_before_code": planned_first,
        "plan_docs": sorted({p for _, p in plan_writes}), "stopped_before_code": bool(stopped),
        "review_started_after_edit": bool(review_after), "reviews": [r for _, r in reviews],
        "post_edit_check_flags_review": bool(post_flags), "pre_flag_reported": pre_flag_reported,
        "code_edit_calls": len(code_edits), "bash_code_writes": len(bash_writes),
        "changed_code_files": len(changed_code), "unattributed_code_changes": unattributed,
        "commits": commits, "oaw_settings_touched": oaw_settings_touched,
        "tests_pass_after": tests.returncode == 0,
        "subtype": result.get("subtype") or ("timeout" if meta.get("timed_out") else "no-result"),
        "turns": result.get("num_turns"), "tool_calls": len(calls), "seconds": meta["seconds"],
        "tokens": meta["tokens"], "tokens_uncached": meta["tokens_uncached"], "thinking_tokens": thinking,
        "apiKeySource": next((e.get("apiKeySource") for e in events
                              if e.get("type") == "system" and e.get("subtype") == "init"), None),
        "served_models": sorted(m for m in served if m),
    }


def grade(scratch: Path):
    ledger = json.loads((scratch / "spend.json").read_text())
    rows = [grade_one(scratch / "runs" / rid) for rid in ledger["runs"]]
    (scratch / "rows.json").write_text(json.dumps(rows, indent=1))
    table = {}
    for r in rows:
        cell = table.setdefault((r["model"], r["arm"]), {"n": 0, "correct": 0, "light": 0, "standard": 0, "deep": 0,
                                                         "tokens": 0})
        cell["n"] += 1
        cell["correct"] += r["correct"]
        cell[r["expected"]] += r["correct"]
        cell["tokens"] += r["tokens"]
    for (model, arm), c in sorted(table.items()):
        print(f"{model:20s} arm {arm}: {c['correct']}/{c['n']}  light {c['light']} standard {c['standard']} "
              f"deep {c['deep']}  tokens {c['tokens']:,}")
    spent = ledger["probes"] + sum(m["tokens"] for m in ledger["runs"].values()) + sum(
        v["tokens"] for v in ledger["void"])
    print(f"spent {spent:,} (probes {ledger['probes']:,}, void {len(ledger['void'])})")
    return rows


def verify(scratch: Path):
    subprocess.run([PY, str(HERE / "verify_modes.py"), str(scratch / "arms"), str(scratch)], check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("setup", "verify", "run", "grade", "order"))
    p.add_argument("--scratch", required=True)
    p.add_argument("--oaw200")
    p.add_argument("--oaw201")
    p.add_argument("--claude")
    p.add_argument("--budget", type=int, default=4_000_000)
    p.add_argument("--probes", type=int, default=0, help="tokens already spent on setup probes")
    p.add_argument("--default-estimate", type=int, default=DEFAULT_ESTIMATE,
                   help="estimate for a scenario not run yet (registered: 500,000)")
    p.add_argument("--sequential", action="store_true", help="one run at a time (deviation 1)")
    p.add_argument("--only-model", default="", help="run only this model block (short name)")
    a = p.parse_args()
    scratch = Path(a.scratch).resolve()
    if a.command == "setup":
        setup(scratch, Path(a.oaw200), Path(a.oaw201))
    elif a.command == "verify":
        verify(scratch)
    elif a.command == "run":
        run_all(scratch, a.claude, a.budget, a.probes, a.default_estimate, a.sequential, a.only_model)
    elif a.command == "grade":
        grade(scratch)
    else:
        for triple in run_order():
            print(" ".join(run_id(t[0], t[2], t[3]) for t in triple))


if __name__ == "__main__":
    sys.exit(main())
