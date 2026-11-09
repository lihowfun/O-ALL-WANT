"""I16 blind grading (PREREG.md). Every report is graded once by Opus 5.5 and once by Codex gpt-6.1-sol (fresh,
tool-less sessions, each inside the same bubblewrap sandbox as the testers with a fresh home holding only the login
file; the event stream must show zero tool calls), with one prompt: the journey, the planted defect's description
(or "no planted defect"), the tester's report with arm, cell and method removed, and the mechanical replay of each
reported defect on the case build and on the clean build. Reports are graded in a hash-shuffled order across cells,
arms and reps. A row without a parsable report is an empty report (no call). A grader call that did not run stops
grading (rerun resumes); a call that returns an unusable verdict is a deviation and stops too.

    python3 i16_grade.py --cases FROZEN --rows A,B --replay replay.jsonl --family opus|codex --out grades.jsonl \
        --claude CLI --codex CLI
Descriptive cheap graders as in X2 (D36): --family luna or haiku; never used by the judge.
"""
import argparse
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
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "X2"))
from i16_run import LIMIT, bwrap  # noqa: E402
from x2_case_tools import parse  # noqa: E402

MODELS = {"opus": ("claude", "claude-opus-5-5", "high"), "codex": ("codex", "gpt-6.1-sol", "high"),
          "haiku": ("claude", "claude-haiku-5-5", None), "luna": ("codex", "gpt-6-luna", "low")}
CHEAP = ("haiku", "luna")
SALT = "i16-2026-11-09"
# Words that name the method or the arm; replaced in what the grader sees (report and replay), counts recorded.
# Host names stay: OAW's own commands and outputs name Claude Code and Codex (--host claude|codex), so only a
# tester's self-identification and model names are removed.
REDACT = [(re.compile(r"(?:\.claude|\.agents)/skills/[\w.-]+(?:/SKILL\.md)?"), "[path]"),
          (re.compile(r"oaw-bugbash", re.I), "[method]"), (re.compile(r"bug-?bash skill", re.I), "[method]"),
          (re.compile(r"(?<!OAW )(?<!OAW's )\b(?:the |full |whole )?recipe(?:'s)?\b(?! (?:after|for|selection|is not))", re.I), "[method]"),
          (re.compile(r"\b(?:arm|condition|variant)\s*[NCDF]\b|\b[NCDF][ -]arm\b", re.I), "[arm]"),
          (re.compile(r"description[- ]only", re.I), "[arm]"),
          (re.compile(r"\b(?:I am|I'm|as an?|this is|running as|tested as)\s+(?:Claude(?: Code)?|Codex|an? (?:Anthropic|OpenAI)[\w ]*)", re.I), "[tester]"),
          (re.compile(r"\bclaude-(?:opus|sonnet|haiku|fable)[\w.-]*|\bgpt-[\d][\w.-]*|\b(?:Opus|Sonnet|Haiku|Fable) \d[\d.]*", re.I), "[model]"),
          (re.compile(r"\b(?:Anthropic|OpenAI)\b"), "[vendor]")]
FIELD_KEEP = {"title": 300, "expected": 1200, "observed": 1500, "evidence": 1500, "step": 400, "checked": 200, "notes": 2000}
MAX_STEPS, MAX_CHECKED = 25, 40
STEP_KEEP = 700


PROMPT = """You are grading one bug-bash report about a command-line tool. A tester got a user journey and the tool,
tried it through the command line, and wrote the report below. You do not know who or what the tester was.

Journey given to the tester:
{goal}

Starting state (commands run before the tester began):
{setup}

{truth}

The tester's report (JSON):
{report}

Mechanical replay: each reported defect's "steps" were run in order in fresh copies of the starting state, on the
case build (the tool exactly as the tester had it) and, when the journey has a planted defect, also on the clean
build (the same tool without the planted defect). Exit codes and output (workspace path shown as <ws>):
{replay}

Grade each reported defect, in order, as exactly one of:
- "planted": it reports the planted defect (the same wrong behavior the description gives; wording may differ) and
  the replay of its steps on the case build shows that wrong behavior. Credit the planted defect at most once. If a
  defect describes the planted defect but its replay does not show the behavior, grade it "unsupported" and set
  "planted_mentioned_only" to true.
- "real_other": a different real defect: the replay shows the behavior on the case build, and the behavior is
  clearly wrong for a user (a crash or traceback on reasonable input, lost or corrupted user data, a wrong exit code
  for a failed step, output that contradicts the tool's own documented behavior or its own other output). Not an
  opinion about design or wording.
- "unsupported": not reproduced by the replay and not otherwise shown, or the behavior is intended or documented
  (see the intended look-alikes, if any), or it is speculation, a style preference or a missing feature.
- "duplicate": the same problem as an earlier defect in this report.

Also say whether the report mentions the planted defect's wrong behavior only as a suspicion, question or untested
idea (in "notes", "checked" or a defect you graded otherwise) without reporting it as a defect ("planted_mentioned_only").

Output only one JSON object, no prose and no code fence:
{{"valid_report": true|false, "per_defect": [{{"index": 0, "verdict": "planted|real_other|unsupported|duplicate",
  "reason": "<one sentence>"}}], "planted_detected": true|false, "planted_mentioned_only": true|false,
  "note": "<one or two sentences>"}}
"valid_report" is false only when the report is empty or not a bug-bash report at all. With no planted defect,
"planted_detected" and "planted_mentioned_only" are false."""


class NotGraded(Exception):
    pass


class NotRun(Exception):
    pass


def grader_call(family, prompt, claude, codex, base, timeout=1800):
    """One fresh, tool-less grading session in the sandbox; returns (text, tokens, raw event stream). Any tool call
    is NotGraded."""
    host, model, effort = MODELS[family]
    work = tempfile.mkdtemp(prefix="g-", dir=base)
    sessions = tempfile.mkdtemp(prefix="gs-", dir=base)
    env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "TERM": "dumb",
           "PATH": "/usr/bin:/bin:" + os.path.dirname(claude if host == "claude" else codex)}
    try:
        if host == "claude":
            argv = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose", "--tools", "", "--model", model,
                    "--strict-mcp-config", "--setting-sources", "project", "--no-session-persistence"]
            argv += ["--effort", effort] if effort else []
            done = subprocess.run(bwrap(work, "claude", argv), env=env, capture_output=True, text=True,
                                  timeout=timeout, stdin=subprocess.DEVNULL)
            text, tokens, tools, source = "", 0, 0, None
            for line in done.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") == "system" and event.get("subtype") == "init":
                    source = event.get("apiKeySource")
                elif event.get("type") == "assistant":
                    tools += sum(1 for b in event.get("message", {}).get("content", []) if b.get("type") == "tool_use")
                elif event.get("type") == "result":
                    text = event.get("result", "") or ""
                    tokens = sum(int(m.get(k) or 0) for m in (event.get("modelUsage") or {}).values() for k in
                                 ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"))
                    if event.get("is_error"):
                        raise NotRun(f"{family} error: {text[:200]}")
            if source != "none":
                raise NotRun(f"{family} billing source {source}")
        else:
            out = os.path.join(work, "last.txt")
            argv = [codex, "exec", "--json", "--model", model, "-c", f'model_reasoning_effort="{effort}"', "--sandbox",
                    "read-only", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "--cd", work, "-o", out, "-"]
            done = subprocess.run(bwrap(work, "codex", argv, sessions), env=env, input=prompt, capture_output=True,
                                  text=True, timeout=timeout)
            tokens, tools = 0, 0
            for line in done.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                item = event.get("item") or {}
                if event.get("type") == "item.completed" and item.get("type") not in (None, "agent_message", "reasoning"):
                    tools += 1
                if event.get("type") == "turn.completed":
                    usage = event.get("usage") or {}
                    tokens += int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)
            text = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
            if LIMIT.search(done.stderr[-600:]):
                raise NotRun(f"{family} usage limit")
        if not text or not tokens or LIMIT.search(text[:300]):
            raise NotRun(f"{family} call did not run: {text[:200]}")
        if tools:
            raise NotGraded(f"the grader made {tools} tool calls")
        return text, tokens, done.stdout
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(sessions, ignore_errors=True)


def redact(text):
    count = 0
    for pattern, mark in REDACT:
        text, n = pattern.subn(mark, text)
        count += n
    return text, count


def truth_text(spec, jid):
    truth = spec["truth"].get(jid)
    if not truth:
        return "Planted defect: none. This journey is a clean control; the tool is unmodified."
    lookalikes = "".join(f"\n- {x}" for x in truth.get("intended_lookalikes") or []) or " none listed"
    return (f"Planted defect ({truth['severity']}): {truth['rubric']}\nHow it shows: {truth['trigger']}\n"
            f"User impact: {truth['user_impact']}\nIntended look-alikes on this journey (not defects):{lookalikes}")


def cut(value, limit):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + f" [...{len(text) - limit} chars cut]"


def anonymous(report):
    """The report the grader sees: every defect kept, each field clipped on its own, always valid JSON."""
    if not isinstance(report, dict):
        return None
    defects = []
    for d in report.get("defects") or []:
        d = d if isinstance(d, dict) else {"title": cut(d, FIELD_KEEP["title"])}
        steps = d.get("steps") if isinstance(d.get("steps"), list) else []
        shown = [cut(x, FIELD_KEEP["step"]) for x in steps[:MAX_STEPS]]
        if len(steps) > MAX_STEPS:
            shown.append(f"[{len(steps) - MAX_STEPS} more steps not shown]")
        defects.append({"title": cut(d.get("title", ""), FIELD_KEEP["title"]), "severity": cut(d.get("severity", ""), 20),
                        "steps": shown, **{k: cut(d.get(k, ""), FIELD_KEEP[k]) for k in ("expected", "observed", "evidence")}})
    checked = report.get("checked") if isinstance(report.get("checked"), list) else []
    shown_checked = [cut(x, FIELD_KEEP["checked"]) for x in checked[:MAX_CHECKED]]
    if len(checked) > MAX_CHECKED:
        shown_checked.append(f"[{len(checked) - MAX_CHECKED} more not shown]")
    keep = {"completed": report.get("completed"), "defects": defects, "checked": shown_checked,
            "notes": cut(report.get("notes", ""), FIELD_KEEP["notes"])}
    return json.dumps(keep, ensure_ascii=False, indent=1)


def clip(text):
    text = text or ""
    return text if len(text) <= STEP_KEEP else text[:STEP_KEEP // 2] + f" ...[{len(text) - STEP_KEEP} chars cut]... " + text[-STEP_KEEP // 2:]


def replay_text(index, entry):
    """One defect's replay as plain text: every step of each build with its exit code, symmetric per-step clipping."""
    lines = [f"Defect {index}:"]
    if entry["case"] is None:
        return f"Defect {index}: not replayed ({entry.get('why')})."
    builds = [("case build", entry["case"])] + ([("clean build", entry["clean"])] if isinstance(entry["clean"], list) else [])
    for name, steps in builds:
        lines.append(f"  {name}:")
        for st in steps:  # the tester wrote the step line, the tool wrote the output: only the step is redacted
            lines.append(f"    $ {redact(st['step'])[0]}\n      exit {st['exit']}\n      stdout: {clip(st['stdout'])}\n"
                         f"      stderr: {clip(st['stderr'])}")
    return "\n".join(lines)


def replay_digest(entries):
    return hashlib.sha256(json.dumps(entries, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def check(verdict, count, planted):
    if not isinstance(verdict, dict) or not isinstance(verdict.get("valid_report"), bool):
        raise NotGraded("no valid_report boolean")
    per = verdict.get("per_defect")
    if not isinstance(per, list) or not all(isinstance(d, dict) for d in per):
        raise NotGraded("per_defect is not a list of objects")
    if sorted(d.get("index") if isinstance(d.get("index"), int) else -1 for d in per) != list(range(count)):
        raise NotGraded(f"per_defect does not cover the {count} reported defects exactly once")
    if any(d.get("verdict") not in ("planted", "real_other", "unsupported", "duplicate") for d in per):
        raise NotGraded("unknown per-defect verdict")
    for key in ("planted_detected", "planted_mentioned_only"):
        if not isinstance(verdict.get(key), bool):
            raise NotGraded(f"no {key} boolean")
    if not planted and (verdict["planted_detected"] or verdict["planted_mentioned_only"]
                        or any(d["verdict"] == "planted" for d in per)):
        raise NotGraded("planted credit on a clean control")
    if verdict["planted_detected"] != any(d["verdict"] == "planted" for d in per):
        raise NotGraded("planted_detected disagrees with the per-defect verdicts")
    if sum(d["verdict"] == "planted" for d in per) > 1:
        raise NotGraded("the planted defect credited more than once")
    if verdict["planted_detected"] and verdict["planted_mentioned_only"]:
        raise NotGraded("detected and mentioned-only at once")
    if not verdict["valid_report"] and verdict["planted_detected"]:
        raise NotGraded("an invalid report cannot carry credit")
    return verdict


def row_key(row):
    return f"{row['cell']}|{row['arm']}|{row['id']}" + (f"|r{row['rep']}" if row.get("rep", 1) != 1 else "")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--cases", required=True)
    p.add_argument("--rows", required=True)
    p.add_argument("--replay", required=True)
    p.add_argument("--family", choices=tuple(MODELS), required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--claude", default="")
    p.add_argument("--codex", default="")
    a = p.parse_args(argv)
    spec = json.load(open(os.path.join(a.cases, "spec.json"), encoding="utf-8"))
    spec_sha = hashlib.sha256(open(os.path.join(a.cases, "spec.json"), "rb").read()).hexdigest()
    # the grader's version covers everything it runs: this file, the runner it imports (sandbox), X2's parse()
    grader_sha = hashlib.sha256(b"".join(open(os.path.join(d, n), "rb").read() for d, n in (
        (HERE, "i16_grade.py"), (HERE, "i16_run.py"), (os.path.join(HERE, "..", "X2"), "x2_case_tools.py")))).hexdigest()
    base = tempfile.mkdtemp(prefix="i16g-", dir=os.environ.get("I16_WS_ROOT") or None)
    rows = [json.loads(l) for path in a.rows.split(",") for l in open(path, encoding="utf-8")]
    rows.sort(key=lambda r: hashlib.sha256(f"{SALT}|{row_key(r)}".encode()).hexdigest())
    replays, replayers = {}, set()
    for line in open(a.replay, encoding="utf-8"):
        entry = json.loads(line)
        if entry["spec_sha256"] != spec_sha:
            raise SystemExit(f"{a.replay}: an entry for another spec")
        jid = entry["key"].split("|")[2]
        if entry["case_digest"] != spec["case_digests"][jid] or entry["case_build"] != spec["built_digests"][jid] \
                or entry["clean_build"] != spec["oaw_src_digest"]:
            raise SystemExit(f"{a.replay}: {entry['key']} #{entry['index']} replayed another case or build")
        replayers.add(entry["replayer_sha256"])
        replays[(entry["key"], entry["index"])] = entry
    if len(replayers) > 1:
        raise SystemExit("replays from more than one replayer version")
    done = {}
    if os.path.exists(a.out):
        for line in open(a.out, encoding="utf-8"):
            old = json.loads(line)
            if (old["grader_sha256"] != grader_sha or old["spec_sha256"] != spec_sha or old["family"] != a.family):
                raise SystemExit(f"{a.out}: {old['key']} graded by another grader or spec version")
            if old["key"] in done:
                raise SystemExit(f"{a.out}: duplicate grade for {old['key']}")
            done[old["key"]] = old
    seen = set()
    for row in rows:
        key = row_key(row)
        if key in seen:
            raise SystemExit(f"two rows share {key}")
        seen.add(key)
        if row.get("spec_sha256") != spec_sha:
            raise SystemExit(f"{key}: row from another spec")
        report = row.get("report")
        defects = report.get("defects") if isinstance(report, dict) and isinstance(report.get("defects"), list) else []
        report_sha = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
        mine = [replays.get((key, i)) for i in range(len(defects))]
        if any(e is None or e["report_sha256"] != report_sha for e in mine):
            raise SystemExit(f"{key}: no replay for this report")
        replay_sha = replay_digest(mine)
        if key in done:
            if done[key]["report_sha256"] != report_sha or done[key].get("replay_sha256") != replay_sha:
                raise SystemExit(f"{a.out}: {key} was graded on another report or replay")
            continue
        planted = spec["kinds"][row["id"]] == "defect"
        tokens, redactions, events, shown_sha, unredacted_sha = 0, 0, "", None, None
        if anonymous(report) is None:
            verdict = {"valid_report": False, "per_defect": [], "planted_detected": False,
                       "planted_mentioned_only": False, "note": "no parsable report"}
        else:
            parts = [replay_text(index, entry) for index, entry in enumerate(mine)]
            journey = json.load(open(os.path.join(a.cases, "cases", row["id"], "journey.json"), encoding="utf-8"))
            shown_report, n1 = redact(anonymous(report))
            shown_replay, n2 = redact("\n".join(parts) or "(no defects reported)")
            redactions = n1 + n2
            fill = dict(goal=journey["goal"], setup="\n".join(f"  {c}" for c in journey["setup"]), truth=truth_text(spec, row["id"]))
            prompt = PROMPT.format(report=shown_report, replay=shown_replay, **fill)
            unredacted = PROMPT.format(report=anonymous(report), replay="\n".join(parts) or "(no defects reported)", **fill)
            shown_sha = hashlib.sha256(prompt.encode()).hexdigest()
            unredacted_sha = hashlib.sha256(unredacted.encode()).hexdigest()
            try:
                text, tokens, events = grader_call(a.family, prompt, a.claude, a.codex, base)
                raw_dir = a.out + ".raw"  # local only: the grader's full event stream, for audit
                os.makedirs(raw_dir, exist_ok=True)
                with open(os.path.join(raw_dir, re.sub(r"[^\w.-]", "_", key) + ".jsonl"), "w", encoding="utf-8") as handle:
                    handle.write(events)
            except NotGraded as exc:
                with open(a.out + ".deviations", "a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"key": key, "family": a.family, "why": str(exc)}, ensure_ascii=False) + "\n")
                print(f"{a.family} {key}: not graded ({exc}); stopping, rerun to resume", flush=True)
                return 6
            except (NotRun, SystemExit, subprocess.TimeoutExpired, ValueError, OSError) as exc:
                with open(a.out + ".deviations", "a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"key": key, "family": a.family, "why": f"call did not run: {str(exc)[:300]}"},
                                            ensure_ascii=False) + "\n")
                print(f"{a.family} {key}: grader call did not run; stopping, rerun to resume", flush=True)
                return 6
            try:
                verdict = check(parse(text), len(defects), planted)
            except (ValueError, NotGraded) as exc:
                with open(a.out + ".deviations", "a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"key": key, "family": a.family, "tokens": tokens, "why": str(exc),
                                             "raw": text[:1500]}, ensure_ascii=False) + "\n")
                print(f"{a.family} {key}: not graded ({exc}); stopping, rerun to resume", flush=True)
                return 6
        verdicts = [d["verdict"] for d in verdict["per_defect"]]
        entry = {"key": key, "cell": row["cell"], "arm": row["arm"], "id": row["id"], "rep": row.get("rep", 1),
                 "kind": spec["kinds"][row["id"]], "family": a.family, "grader_sha256": grader_sha, "spec_sha256": spec_sha,
                 "report_sha256": report_sha, "replay_sha256": replay_sha, "replayer_sha256": next(iter(replayers), None),
                 "row_runner_sha256": row.get("runner_sha256"), "verdict": verdict,
                 "tokens": tokens, "detected": int(bool(verdict["planted_detected"])),
                 "mentioned_only": int(bool(verdict["planted_mentioned_only"]) and not verdict["planted_detected"]),
                 "unsupported": verdicts.count("unsupported"), "real_other": verdicts.count("real_other"),
                 "reported": len(defects), "valid": bool(verdict["valid_report"]), "redactions": redactions,
                 "tool_calls": 0, "events_sha256": hashlib.sha256(events.encode()).hexdigest() if events else None,
                 "prompt_sha256": shown_sha, "unredacted_prompt_sha256": unredacted_sha}
        with open(a.out, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"{a.family} graded {key}: detected {entry['detected']} unsupported {entry['unsupported']} "
              f"real_other {entry['real_other']} tokens {tokens:,}", flush=True)
    shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
