"""X2 review runner (PREREG.md): one fresh session per (cell, arm, case) in a fresh workspace, subscription billing.

Cells: `claude` (Claude Code, claude-opus-5-5 high) and `codex` (Codex CLI, gpt-6.1-sol, reasoning high).
Arms in each cell (X, the other family's single review, is that family's N row and is not run here):
  N  the case files only; the review task prompt.
  R  N plus the frozen checklist (checklist_R.md, between the R markers) appended to the prompt.
  E  the case files plus OAW 2.0.1 (`oaw.py init --host <cell>`, default recipe with the bundled EGM); the prompt
     asks for the installed egm-review entry with Step uninterrupted, then the same JSON report.
Claude settings follow the EGM self-test (Read, Write, Glob, Grep, Agent, Skill; acceptEdits; project settings only;
no MCP; no session kept). Codex: `codex exec --sandbox workspace-write`, user config ignored, sessions kept only
long enough to sum every thread's token use (the rollout files this run created are moved into the raw folder).
A session that hit a usage limit, used 0 tokens, ended in an error before a result, or billed anything but the
subscription is not a run: deviations.jsonl, and the runner stops (rerun resumes). The Claude cell starts a run
only if the X2 Claude spend plus the arm's largest run so far fits under --budget.

    python3 x2_run.py --cell claude --cases CASES --order ids.json --oaw-src DIR --claude CLI --out DIR --budget N --spent N
    python3 x2_run.py --cell codex  --cases CASES --order ids.json --oaw-src DIR --codex CLI --out DIR
Calibration (D36): --arms N --reps 3 on the calibration cases, into its own --out.
Resume refuses rows written by another runner version or another prompt (no mixed-version results).
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
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = """Review the design in this workspace. Read README.md, docs/design.md, all docs/adr-*.md files and src/*.py.
Assess concrete design correctness and consistency with current accepted decisions. Superseded decisions and
historical notes are evidence to check, not authority. Distinguish a factual defect from an open question,
conditional risk or style preference. Do not assume planned tests have already passed. Do not invent requirements
beyond the supplied sources. Do not browse the web and do not change README.md, docs/ or src/; only write review
files.

{treatment}

Finally write one JSON report to review_out/report.json, at most 900 words, with the fields "completed" (boolean),
"findings" (array of objects with "location", "claim", "evidence", "rationale", "severity") and "uncertainties"
(array). Findings must cite source file and line evidence and describe actual effects. Put template or style
preferences and conditional issues in uncertainties. Do not name your method, tools, reviewers or review stages
inside findings or uncertainties. Your final message gives only the report path and the completion status."""
E_TREATMENT = """Run the project's design review on docs/design.md: read the installed egm-review skill file
(.claude/skills/egm-review/SKILL.md or .agents/skills/egm-review/SKILL.md) and follow the upstream entry it names,
with TargetFile docs/design.md, GoldfishContext README.md, every docs/adr-*.md file and src/, and Step uninterrupted
(consolidated report with all review rubrics, all stages without stopping, no changes to the design). Base the
JSON report below on its consolidated findings."""
LIMIT = re.compile(r"hit your (?:\w+ )?limit|usage limit reached|you've reached your usage limit|limit \W* resets \d", re.I)
MIN_E_AGENTS = 5  # an E attempt with fewer reviewer launches did not deliver the full workflow (PREREG)
FIRST_ESTIMATE = {"N": 150_000, "R": 150_000, "E": 1_430_000}


def r_treatment():
    text = open(os.path.join(HERE, "checklist_R.md"), encoding="utf-8").read()
    return text.split("<!-- R:begin -->\n", 1)[1].split("<!-- R:end -->", 1)[0].strip()


def tree_digest(root):
    """sha256 over the case files only (README.md, docs/, src/), so an install or a report does not count."""
    digest = hashlib.sha256()
    paths = [os.path.join(root, "README.md")] if os.path.exists(os.path.join(root, "README.md")) else []
    for sub in ("docs", "src"):
        for base, dirs, names in sorted(os.walk(os.path.join(root, sub))):
            dirs.sort()
            paths += [os.path.join(base, n) for n in sorted(names)]
    for path in paths:
        digest.update(os.path.relpath(path, root).encode() + b"\0" + open(path, "rb").read() + b"\0")
    return digest.hexdigest()


def prepare(cell, arm, case_dir, work, oaw_src, frozen=None):
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(case_dir, work)
    facts = {"case_digest": tree_digest(work)}
    if frozen is not None and frozen.get(os.path.basename(case_dir)) != facts["case_digest"]:
        raise SystemExit(f"{case_dir}: case files differ from the frozen spec")
    if arm == "E":
        done = subprocess.run(["/usr/bin/python3", os.path.join(oaw_src, "scripts", "oaw.py"), "init", "--target", work,
                               "--host", cell, "--json"], capture_output=True, text=True)
        init = json.loads(done.stdout or "{}")
        if init.get("status") != "installed" or "egm-review" not in init.get("skills", []):
            raise SystemExit(f"oaw init did not install egm-review: {done.stderr[-300:]}")
        facts["oaw_skills"] = init["skills"]
    return facts


def run_claude(work, prompt, claude, timeout):
    env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "TERM": "dumb",
           "PATH": ":".join([os.path.dirname(claude), "/usr/bin", "/bin"])}
    argv = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose", "--model", "claude-opus-5-5",
            "--effort", "high", "--tools", "Read,Write,Glob,Grep,Agent,Skill", "--permission-mode", "acceptEdits",
            "--setting-sources", "project", "--strict-mcp-config", "--no-session-persistence"]
    started = time.time()
    try:
        done = subprocess.run(argv, cwd=work, env=env, capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
        stdout, code = done.stdout, done.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        code = "timeout"
    row = {"exit": code, "seconds": round(time.time() - started, 1), "raw": stdout, "agents": 0, "tools": {}}
    final = ""
    streamed = {}
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
            row["agents_seen"] = sorted(event.get("agents") or [])
        elif event.get("type") == "assistant":
            message = event.get("message", {})
            if message.get("id") and message.get("usage"):
                streamed[message["id"]] = message["usage"]
            if event.get("parent_tool_use_id"):
                continue
            for block in message.get("content", []):
                if block.get("type") == "tool_use":
                    row["tools"][block["name"]] = row["tools"].get(block["name"], 0) + 1
                    if block["name"] in ("Agent", "Task"):
                        row["agents"] += 1
                        spec_ = block.get("input") or {}
                        row.setdefault("agent_paths", []).append(str(spec_.get("subagent_type") or spec_.get("description") or "")[:80])
        elif event.get("type") == "result":
            final = event.get("result", "") or ""
            row["result_seen"] = True
            row["is_error"] = event.get("is_error")
            row["subtype"] = event.get("subtype")
            models = event.get("modelUsage") or {}
            row["model_usage"] = models
            row["tokens_total"] = sum(int(m.get(k) or 0) for m in models.values() for k in
                                      ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"))
            row["tokens_noncache"] = sum(int(m.get(k) or 0) for m in models.values() for k in
                                         ("inputTokens", "outputTokens", "cacheCreationInputTokens"))
    row["streamed_tokens"] = sum(int(u.get(k) or 0) for u in streamed.values() for k in
                                 ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    if not row.get("tokens_total"):  # a timeout or a cut session has no result event: count what streamed
        row["tokens_total"] = row["streamed_tokens"]
        row["tokens_noncache"] = sum(int(u.get(k) or 0) for u in streamed.values() for k in
                                     ("input_tokens", "output_tokens", "cache_creation_input_tokens"))
        row["tokens_from"] = "stream (lower bound)"
    row["final"] = final[:2000]
    row["limit_seen"] = bool(LIMIT.search(final[:300])) or (row.get("is_error") and "limit" in final[:300].lower())
    return row


def codex_rollouts():
    return set(glob.glob(os.path.join(os.environ["HOME"], ".codex", "sessions", "**", "rollout-*.jsonl"), recursive=True))


def rollout_meta(path):
    """A rollout's session_meta payload (id, parent_thread_id, cwd, agent_path), or {}."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for _ in range(5):
                event = json.loads(handle.readline() or "{}")
                if event.get("type") == "session_meta":
                    return event.get("payload") or {}
    except (OSError, ValueError):
        return {}
    return {}


def rollout_cwd(path):
    """The working folder recorded in a rollout's session_meta (subagent threads share the parent's)."""
    cwd = rollout_meta(path).get("cwd")
    return os.path.realpath(cwd) if cwd else None


def rollout_tokens(path):
    """(total, non-cache) from the last token_count event of one rollout file."""
    last = None
    for line in open(path, encoding="utf-8", errors="replace"):
        if '"token_count"' in line:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            info = (event.get("payload") or {}).get("info") or {}
            last = info.get("total_token_usage") or last
    if not last:
        return 0, 0
    total = int(last.get("input_tokens") or 0) + int(last.get("output_tokens") or 0)
    return total, total - int(last.get("cached_input_tokens") or 0)


def run_codex(work, prompt, codex, timeout, raw_dir, tag):
    env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "TERM": "dumb",
           "PATH": ":".join([os.path.dirname(codex), "/usr/bin", "/bin"])}
    argv = [codex, "exec", "--json", "--model", "gpt-6.1-sol", "-c", 'model_reasoning_effort="high"',
            "--sandbox", "workspace-write", "--skip-git-repo-check", "--ignore-user-config", "--cd", work, "-"]
    before = codex_rollouts()
    started = time.time()
    try:
        done = subprocess.run(argv, cwd=work, env=env, input=prompt, capture_output=True, text=True, timeout=timeout)
        stdout, code, stderr = done.stdout, done.returncode, done.stderr
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        code = "timeout"
    row = {"exit": code, "seconds": round(time.time() - started, 1), "raw": stdout, "agents": 0, "tools": {},
           "api_key_source": "chatgpt", "model": "gpt-6.1-sol", "stderr_tail": stderr[-400:]}
    texts, errors, parent = [], [], {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    root_id = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "thread.started":
            root_id = event.get("thread_id")
        if kind == "item.completed":
            item = event.get("item") or {}
            itype = item.get("type")
            if itype == "agent_message" and str(item.get("text", "")).strip():
                texts.append(item["text"])
            elif itype and itype != "reasoning":
                name = itype if itype != "collab_tool_call" else f"collab:{item.get('tool')}"
                row["tools"][name] = row["tools"].get(name, 0) + 1
        elif kind == "turn.completed":
            row["result_seen"] = True
            for key in parent:
                parent[key] += int((event.get("usage") or {}).get(key) or 0)
        elif kind in ("turn.failed", "error"):
            errors.append(json.dumps(event)[:300])
    # The run's thread tree: the root thread (thread.started) and its descendants by parent_thread_id, among the
    # rollouts this run created in its own workspace. Spawned threads are the reviewer launches (wait calls are not).
    found = {p: rollout_meta(p) for p in codex_rollouts() - before if rollout_cwd(p) == os.path.realpath(work)}
    by_id = {m.get("id"): p for p, m in found.items() if m.get("id")}
    tree = {root_id} if root_id else set()
    grew = True
    while grew:
        grew = False
        for p, m in found.items():
            if m.get("id") not in tree and m.get("parent_thread_id") in tree:
                tree.add(m["id"])
                grew = True
    rollouts = sorted(by_id[i] for i in tree if i in by_id)
    stray = sorted(set(found) - set(rollouts))
    os.makedirs(os.path.join(raw_dir, f"{tag}-rollouts"), exist_ok=True)
    for path in rollouts + stray:
        shutil.move(path, os.path.join(raw_dir, f"{tag}-rollouts", os.path.basename(path)))
    rollouts = [os.path.join(raw_dir, f"{tag}-rollouts", os.path.basename(p)) for p in rollouts]
    children = [found_meta for found_meta in (rollout_meta(p) for p in rollouts) if found_meta.get("id") != root_id]
    row["threads"] = len(rollouts)
    row["stray_rollouts"] = len(stray)
    row["agents"] = len(children)
    row["agent_paths"] = sorted(m.get("agent_path") or "" for m in children)
    row["parent_usage"] = parent
    root_path = by_id.get(root_id)
    child_totals = [rollout_tokens(p) for p in rollouts if rollout_meta(p).get("id") != root_id]
    root_total = rollout_tokens(os.path.join(raw_dir, f"{tag}-rollouts", os.path.basename(root_path))) if root_path else (0, 0)
    row["child_usage_missing"] = sum(1 for t, _n in child_totals if not t)
    if root_total[0]:
        row["tokens_from"] = "rollouts (root and descendants)"
    else:  # no root rollout or no usage in it: the parent's streamed usage stands in, never the children alone
        root_total = (parent["input_tokens"] + parent["output_tokens"],
                      parent["input_tokens"] - parent["cached_input_tokens"] + parent["output_tokens"])
        row["tokens_from"] = "parent stream + child rollouts" + ("" if not root_path else " (root rollout had no usage)")
    row["tokens_total"] = root_total[0] + sum(t for t, _n in child_totals)
    row["tokens_noncache"] = root_total[1] + sum(n for _t, n in child_totals)
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
        return "0 tokens"  # checked before the timeout rule: a session that never started is not a run (D30)
    if row["exit"] == "timeout":
        return ""  # a timeout is a run (PREREG); its report, if any, is graded
    if not row.get("result_seen") or row.get("is_error") or row["exit"] != 0:
        return f"error (exit {row['exit']}, subtype {row.get('subtype')})"
    return ""


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell", choices=("claude", "codex"), required=True)
    parser.add_argument("--cases", required=True, help="folder with cases/<id>/")
    parser.add_argument("--order", required=True, help="JSON list of case ids")
    parser.add_argument("--oaw-src", required=True)
    parser.add_argument("--claude", default="")
    parser.add_argument("--codex", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--budget", type=int, default=0)
    parser.add_argument("--spent", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--only", default="", help="arm:case,... (pilots)")
    parser.add_argument("--arms", default="N,R,E", help="arms to run, in rotation order (calibration: N)")
    parser.add_argument("--reps", type=int, default=1, help="runs per case and arm (calibration: 3)")
    args = parser.parse_args(argv)
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "OPENAI_API_KEY"):
        if os.environ.get(key):
            raise SystemExit(f"{key} is set; subscription only")
    order = json.load(open(args.order, encoding="utf-8"))
    raw_dir = os.path.join(args.out, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    rows_path, dev_path = os.path.join(args.out, "rows.jsonl"), os.path.join(args.out, "deviations.jsonl")
    only = set(filter(None, args.only.split(",")))
    treatments = {"N": "", "R": r_treatment(), "E": E_TREATMENT}
    spec_path = os.path.join(args.cases, "spec.json")
    frozen = json.load(open(spec_path, encoding="utf-8")).get("case_digests") if os.path.exists(spec_path) else None
    runner_sha = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    spec_sha = hashlib.sha256(open(spec_path, "rb").read()).hexdigest() if os.path.exists(spec_path) else None
    oaw_sha = hashlib.sha256()
    for base, dirs, names in sorted(os.walk(args.oaw_src)):
        dirs.sort()
        for name in sorted(names):
            path = os.path.join(base, name)
            oaw_sha.update(os.path.relpath(path, args.oaw_src).encode() + b"\0" + open(path, "rb").read() + b"\0")
    oaw_sha = oaw_sha.hexdigest()
    base_arms = [a for a in ["N", "R", "E"] if a in set(args.arms.split(","))]
    prompts = {arm: TASK.format(treatment=treatments[arm]).replace("\n\n\n", "\n\n") for arm in base_arms}
    prompt_sha = {arm: hashlib.sha256(text.encode()).hexdigest() for arm, text in prompts.items()}

    def ledger():
        spent, done, largest = args.spent, set(), dict(FIRST_ESTIMATE)
        seen = {}
        for name in ("rows.jsonl", "deviations.jsonl"):
            path = os.path.join(args.out, name)
            if os.path.exists(path):
                for line in open(path, encoding="utf-8"):
                    row = json.loads(line)
                    spent += row.get("tokens_total") or 0
                    seen[row["arm"]] = max(seen.get(row["arm"], 0), row.get("tokens_total") or 0)
                    if name == "rows.jsonl":
                        if (row.get("runner_sha256") != runner_sha or row.get("prompt_sha256") != prompt_sha.get(row["arm"])
                                or row.get("spec_sha256") != spec_sha or row.get("oaw_src_sha256") != oaw_sha):
                            raise SystemExit(f"{path}: {row['arm']}-{row['id']} was written by another runner or "
                                             "prompt version; a mixed-version result set is not allowed (PREREG)")
                        done.add((row["arm"], row["id"], row.get("rep", 1)))
        largest.update(seen)
        return spent, done, largest

    for index, cid in enumerate(order):
        arms = base_arms[index % len(base_arms):] + base_arms[:index % len(base_arms)]
        for rep, arm in [(r, a) for r in range(1, args.reps + 1) for a in arms]:
            spent, done, largest = ledger()
            if (arm, cid, rep) in done or (only and f"{arm}:{cid}" not in only):
                continue
            if args.cell == "claude" and spent + largest[arm] > args.budget:
                print(f"budget guard: {spent:,} spent, {arm} {cid} needs about {largest[arm]:,}; stopping", flush=True)
                return 3
            key = f"{arm}-{cid}" if args.reps == 1 else f"{arm}-{cid}.r{rep}"
            work = os.path.join(args.out, "ws", key)
            facts = prepare(args.cell, arm, os.path.join(args.cases, "cases", cid), work, args.oaw_src, frozen)
            prompt = prompts[arm]
            attempt = len([n for n in os.listdir(raw_dir) if n.startswith(f"{key}.a") and n.endswith(".jsonl")]) + 1
            tag = f"{key}.a{attempt}"
            if args.cell == "claude":
                row = run_claude(work, prompt, args.claude, args.timeout)
            else:
                row = run_codex(work, prompt, args.codex, args.timeout, raw_dir, tag)
            with open(os.path.join(raw_dir, f"{tag}.jsonl"), "w", encoding="utf-8") as handle:
                handle.write(row.pop("raw"))
            row.update({"cell": args.cell, "arm": arm, "id": cid, "rep": rep, "prepared": facts, "attempt": attempt,
                        "prompt_sha256": prompt_sha[arm], "runner_sha256": runner_sha, "spec_sha256": spec_sha,
                        "oaw_src_sha256": oaw_sha})
            if arm == "E":  # compliance checks reviewer launches only, never stage content (PREREG limits)
                row["e_compliant"] = row["agents"] >= MIN_E_AGENTS
            report_path = os.path.join(work, "review_out", "report.json")
            try:
                row["report"] = json.load(open(report_path, encoding="utf-8"))
            except (OSError, ValueError) as exc:
                row["report"], row["report_error"] = None, str(exc)[:200]
            row["review_files"] = sorted(os.path.relpath(p, work) for p in glob.glob(os.path.join(work, "review_out", "**"), recursive=True) if os.path.isfile(p))
            row["sources_changed"] = tree_digest(work) != facts["case_digest"]
            keep = os.path.join(raw_dir, f"{tag}-review_out")
            shutil.rmtree(keep, ignore_errors=True)
            if os.path.isdir(os.path.join(work, "review_out")):
                shutil.copytree(os.path.join(work, "review_out"), keep)
            reason = not_run(row, args.cell)
            if reason:
                with open(dev_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(dict(row, reason=reason), ensure_ascii=False) + "\n")
                print(f"{args.cell} {tag}: not a run ({reason}); stopping, rerun to resume", flush=True)
                return 4 if reason.startswith("billing") else 5
            with open(rows_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"{args.cell} {tag}: exit {row['exit']} {row['seconds']}s agents {row['agents']} report "
                  f"{'ok' if row['report'] else 'MISSING'} tokens {row['tokens_total']:,} (non-cache "
                  f"{row['tokens_noncache']:,}) spent {ledger()[0]:,}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
