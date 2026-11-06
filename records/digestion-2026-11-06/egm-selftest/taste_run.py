"""EGM self-test runner (PREREG.md): the frozen egm-local design-review cases, one fresh `claude -p` session per
(arm, case, repeat). Subscription billing only.

Adapted from ../../digestion-2026-11-03/taste-court-skill/taste_run.py. Each (arm, case) has one fixed workspace
(the E workspaces carry EGM's project-scope plugin install, which is tied to the project path); after every run
the files the session created are copied out, any change to a pristine file is recorded, and the workspace is
restored from its pristine tar, so one trial's files never reach the next. Token use counts sub-agents too (the
result event's per-model totals, cross-checked against the stream). The raw stream-json stays local.

    arms.json: {"N": {"workspaces": {"orders": "<dir>", ...}, "pristine": {"orders": "<tar>", ...}},
                "E": {..., "add_dir": "<resolved plugin root>"}, "P": {...}}
"""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time

CASES = ("orders", "events", "clean")
ORDERS = {1: ("N", "E", "P"), 2: ("E", "P", "N"), 3: ("P", "N", "E")}

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

NATIVE = ("Use your normal reasoning and tools. Independent fresh reviewers (sub-agents) are permitted if useful, "
          "at most nine.")
EGM = ("TargetFile: docs/design.md\nGoldfishContext: README.md, every docs/adr-*.md file, every src/*.py file\n"
       "Step: uninterrupted\n\n"
       "Run the official uninterrupted full flow (Consolidated report with all review rubrics) as the skill describes, "
       "with real fresh reviewer contexts; do not stop for checkpoints and do not apply fixes to the design.")
PROMPTS = {"N": TASK.format(treatment=NATIVE), "P": TASK.format(treatment=NATIVE),
           "E": "/egm:egm-review " + EGM + "\n\n" + TASK.format(treatment="When the consolidated report is written, "
                                                                   "turn its findings into the JSON report below.")}
TOOLS = "Read,Write,Glob,Grep,Agent"
ALLOWED = ["Read", "Write", "Glob", "Grep", "Agent"]
# A session cut by the subscription's usage limit (or one that spent no tokens) did not run: it is never a row.
LIMIT = re.compile(r"hit your (?:\w+ )?limit|usage limit reached|limit \W* resets \d", re.I)
CONTAMINATION = (".oaw/integrations/egm", "plugins/cache/egm", "egm-review", "egm-", "/egm/")


def _usage_sum(usage):
    return sum(int(usage.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                                                 "cache_read_input_tokens"))


def _pristine(tar_path):
    files = {}
    with tarfile.open(tar_path) as archive:
        for member in archive:
            if member.isfile():
                files[member.name] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    return files


def _walk(root):
    out = {}
    for base, dirs, names in os.walk(root):
        for name in names:
            path = os.path.join(base, name)
            if os.path.islink(path):
                continue
            rel = os.path.relpath(path, root)
            out[rel] = path
    return out


def restore(workspace, tar_path):
    for entry in os.listdir(workspace):
        target = os.path.join(workspace, entry)
        if os.path.isdir(target) and not os.path.islink(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
    with tarfile.open(tar_path) as archive:
        archive.extractall(workspace, filter="data")


def run_one(arm, spec, case, rep, claude, out, timeout, model, effort, setting_sources):
    workspace, tar_path = spec["workspaces"][case], spec["pristine"][case]
    pristine = _pristine(tar_path)
    restore(workspace, tar_path)
    env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "TERM": "dumb", "DISABLE_AUTOUPDATER": "1",
           "PATH": ":".join([os.path.dirname(claude), "/usr/bin", "/bin"])}
    argv = [claude, "-p", PROMPTS[arm], "--output-format", "stream-json", "--verbose", "--tools", TOOLS,
            "--allowedTools", *ALLOWED, "--permission-mode", "acceptEdits", "--strict-mcp-config",
            "--setting-sources", setting_sources, "--no-session-persistence"]
    if spec.get("add_dir"):
        argv += ["--add-dir", spec["add_dir"]]
    if model:
        argv += ["--model", model]
    if effort:
        argv += ["--effort", effort]
    started = time.time()
    try:
        done = subprocess.run(argv, cwd=workspace, env=env, capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
        stdout, code = done.stdout, done.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        code = "timeout"
    seconds = round(time.time() - started, 1)
    key = f"{arm}-{case}-r{rep}"
    with open(os.path.join(out, "raw", key + ".jsonl"), "w", encoding="utf-8") as handle:
        handle.write(stdout)
    row = {"arm": arm, "id": case, "rep": rep, "exit": code, "seconds": seconds, "api_key_source": None,
           "answer": "", "tools": {}, "agent_calls": 0, "agent_calls_nested": 0, "subagent_types": {},
           "usage_main": {}, "model_usage": {}, "subagent_models": [], "turns": None, "is_error": None,
           "plugins": [], "egm_command": None, "permission_denials": 0, "contamination": []}
    seen, sub_models = {}, set()
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init" and not event.get("parent_tool_use_id"):
            row["api_key_source"] = event.get("apiKeySource")
            row["model"] = event.get("model")
            row["claude_code_version"] = event.get("claude_code_version")
            row["plugins"] = [p.get("name") for p in event.get("plugins") or []]
            commands = event.get("slash_commands") or []
            row["egm_command"] = "egm:egm-review" in commands
            row["agents_available"] = sorted(a for a in (event.get("agents") or []) if "egm" in str(a))
        elif kind == "assistant":
            message = event.get("message", {})
            nested = bool(event.get("parent_tool_use_id"))
            if nested:
                sub_models.add(message.get("model"))
            if message.get("id") and message.get("usage"):
                seen[message["id"]] = _usage_sum(message["usage"])
            for block in message.get("content", []):
                if block.get("type") == "text" and LIMIT.search(block.get("text") or "") and \
                        message.get("model") == "<synthetic>":
                    row["usage_limited"] = True
                if block.get("type") != "tool_use":
                    continue
                name, tool_input = block["name"], block.get("input", {}) or {}
                if name in ("Agent", "Task"):
                    kind_name = str(tool_input.get("subagent_type") or "general-purpose")
                    row["subagent_types"][kind_name] = row["subagent_types"].get(kind_name, 0) + 1
                    if nested:
                        row["agent_calls_nested"] += 1
                    else:
                        row["agent_calls"] += 1
                if not nested:
                    row["tools"][name] = row["tools"].get(name, 0) + 1
                if arm != "E":
                    text = json.dumps(tool_input).replace(workspace, "<ws>")
                    hits = [c for c in CONTAMINATION if c in text]
                    if hits:
                        row["contamination"].append({"tool": name, "hits": hits, "input": text[:200]})
        elif kind == "result":
            if LIMIT.search(str(event.get("result") or "")) or event.get("api_error_status") == 429:
                row["usage_limited"] = True
            row["answer"] = event.get("result", "") or ""
            row["usage_main"] = event.get("usage", {}) or {}
            row["model_usage"] = event.get("modelUsage", {}) or {}
            row["turns"] = event.get("num_turns")
            row["is_error"] = event.get("is_error")
            row["permission_denials"] = len(event.get("permission_denials") or [])
    model_total = sum(int(m.get(k) or 0) for m in row["model_usage"].values()
                      for k in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"))
    row["tokens_stream"] = sum(seen.values())
    row["tokens_model_usage"] = model_total
    row["tokens_total"] = max(model_total, row["tokens_stream"], _usage_sum(row["usage_main"]))
    row["subagent_models"] = sorted(m for m in sub_models if m)
    row["tool_calls"] = sum(row["tools"].values())
    # Files after the run: copy new ones out, record changes to pristine files, then restore the workspace.
    after = _walk(workspace)
    artifacts = os.path.join(out, "artifacts", key)
    os.makedirs(artifacts, exist_ok=True)
    row["new_files"], row["mutated"] = [], []
    for rel, path in sorted(after.items()):
        digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if rel not in pristine:
            row["new_files"].append(rel)
            target = os.path.join(artifacts, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(path, target)
        elif pristine[rel] != digest:
            row["mutated"].append(rel)
    row["missing"] = sorted(set(pristine) - set(after))
    report_path = os.path.join(artifacts, "review_out", "report.json")
    row["report_found"] = os.path.exists(report_path)
    row["report"] = None
    if row["report_found"]:
        try:
            row["report"] = json.load(open(report_path, encoding="utf-8"))
        except ValueError:
            row["report_parse_error"] = True
    restore(workspace, tar_path)
    return row


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--arms", required=True)
    parser.add_argument("--claude", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--cases", default=",".join(CASES))
    parser.add_argument("--cap", type=int, default=9_000_000, help="all arms together (PREREG)")
    parser.add_argument("--estimate", default="", help="first estimate per arm before it has run, e.g. E=1300000")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--model", default="claude-opus-5-5")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--setting-sources", default="project")
    args = parser.parse_args(argv)
    arms = json.load(open(args.arms, encoding="utf-8"))
    largest = {arm: 0 for arm in "NEP"}
    for item in filter(None, args.estimate.split(",")):
        arm, value = item.split("=")
        largest[arm] = int(value)
    spent = {arm: 0 for arm in "NEP"}
    os.makedirs(os.path.join(args.out, "raw"), exist_ok=True)
    rows_path = os.path.join(args.out, "rows.jsonl")
    deviations_path = os.path.join(args.out, "deviations.jsonl")
    done = set()
    if os.path.exists(rows_path):
        for line in open(rows_path, encoding="utf-8"):
            row = json.loads(line)
            done.add((row["arm"], row["id"], row["rep"]))
            spent[row["arm"]] += row["tokens_total"]
            largest[row["arm"]] = max(largest[row["arm"]], row["tokens_total"])
    lost = 0  # tokens spent by sessions the usage limit cut off: they count against the cap, never as rows
    if os.path.exists(deviations_path):
        lost = sum(json.loads(line).get("tokens_total", 0) for line in open(deviations_path, encoding="utf-8"))
    for rep in range(1, args.repeat + 1):
        for case in args.cases.split(","):
            todo = [arm for arm in ORDERS[rep] if arm in arms and (arm, case, rep) not in done]
            if not todo:
                continue
            # Group guard: a (case, repeat) starts only when all its arms still fit under the pooled cap, each arm
            # estimated by its largest run so far.
            total = sum(spent.values()) + lost
            if total + sum(largest[arm] for arm in todo) > args.cap:
                print(f"budget guard: {total:,} spent, next group about {sum(largest[a] for a in todo):,}; "
                      f"not starting {case} r{rep}", flush=True)
                return 3
            for arm in todo:
                row = run_one(arm, arms[arm], case, rep, args.claude, args.out, args.timeout, args.model,
                              args.effort, args.setting_sources)
                if row.get("usage_limited") or row["tokens_total"] == 0:
                    lost += row["tokens_total"]
                    with open(deviations_path, "a", encoding="utf-8") as handle:
                        handle.write(json.dumps({"key": f"{row['arm']}|{row['id']}|{row['rep']}", "at": time.time(),
                                                 "reason": "usage limit" if row.get("usage_limited") else "no tokens",
                                                 "tokens_total": row["tokens_total"], "seconds": row["seconds"]}) + "\n")
                    print(f"{arm} {case} r{rep}: cut by the usage limit after {row['tokens_total']:,} tokens; not a "
                          f"row; stopping cleanly (rerun to resume)", flush=True)
                    return 6
                with open(rows_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                spent[arm] += row["tokens_total"]
                largest[arm] = max(largest[arm], row["tokens_total"])
                print(f"{arm} {case} r{rep}: exit {row['exit']} {row['seconds']}s agents {row['agent_calls']}"
                      f"+{row['agent_calls_nested']} report {row['report_found']} mutated {len(row['mutated'])} "
                      f"denials {row['permission_denials']} contamination {len(row['contamination'])} "
                      f"tokens {row['tokens_total']:,} (all {sum(spent.values()) + lost:,})", flush=True)
                if row["api_key_source"] not in (None, "none"):
                    print(f"billing source is {row['api_key_source']}, not the subscription; stopping", flush=True)
                    return 4
                if arm == "E" and not (row["egm_command"] and "egm" in row["plugins"]):
                    print("the EGM plugin did not load in arm E; stopping", flush=True)
                    return 5
                if arm != "E" and "egm" in row["plugins"]:
                    print(f"EGM loaded in arm {arm}; stopping", flush=True)
                    return 5
                if row["exit"] not in (0, "timeout") and not row["report_found"]:
                    print(f"run failed without a report (exit {row['exit']}); stopping", flush=True)
                    return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())
