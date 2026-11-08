"""X2 blind grading (PREREG.md): every report is graded once by Opus 5.5 (claude -p, no tools, empty folder) and once
by Codex gpt-6.1-sol (codex exec, read-only, empty folder), with the same prompt: the EGM self-test grader's
prompt (../../digestion-2026-11-06/egm-selftest/taste_grade.py, same masking and anonymity) plus one field,
"mentioned_only", for planted defects a review raises only as an uncertainty, question or conditional risk.
Reports are graded in a hash-shuffled order across both cells and all arms. A row without a parsable report is an
empty review (no call). A grader call that did not run stops grading (rerun resumes).

    python3 x2_grade.py --cases CASES --rows A/rows.jsonl,B/rows.jsonl --family opus|codex --out grades-opus.jsonl \
        --claude CLI --codex CLI
Descriptive cheap graders (D36, Figma intake I18): --family luna (gpt-6-luna, reasoning low, ChatGPT plan) or haiku
(claude-haiku-5-5). Same prompt and checks; their grades never enter the decision (x2_judge.py reads opus and codex).
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec_ = importlib.util.spec_from_file_location(
    "taste_grade", os.path.join(HERE, "..", "..", "digestion-2026-11-06", "egm-selftest", "taste_grade.py"))
TG = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(TG)
sys.path.insert(0, HERE)
from x2_case_tools import LIMIT, call, parse  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402

CHEAP = {"luna": ("codex", "gpt-6-luna", "low"), "haiku": ("claude", "claude-haiku-5-5", None)}


def cheap_call(family, prompt, claude, codex, timeout=1800):
    """call() from x2_case_tools with the cheap model; same isolation, billing and not-run checks."""
    host, model, effort = CHEAP[family]
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="x2grade-") as cwd:
        if host == "claude":
            env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "PATH": os.path.dirname(claude) + ":/usr/bin:/bin"}
            done = subprocess.run([claude, "-p", prompt, "--output-format", "json", "--tools", "", "--strict-mcp-config",
                                   "--setting-sources", "project", "--no-session-persistence", "--model", model],
                                  cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout,
                                  stdin=subprocess.DEVNULL)
            envelope = json.loads(done.stdout)
            usage = envelope.get("usage") or {}
            tokens = sum(int(usage.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                                                           "cache_read_input_tokens"))
            text = envelope.get("result", "") or ""
            if envelope.get("is_error") or LIMIT.search(text[:300]) or not tokens:
                raise SystemExit(f"{family} call did not run: {text[:200]}")
        else:
            env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "PATH": os.path.dirname(codex) + ":/usr/bin:/bin"}
            out = os.path.join(cwd, "last.txt")
            done = subprocess.run([codex, "exec", "--json", "--model", model, "-c", f'model_reasoning_effort="{effort}"',
                                   "--sandbox", "read-only", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config",
                                   "--cd", cwd, "-o", out, "-"], cwd=cwd, env=env, input=prompt, capture_output=True,
                                  text=True, timeout=timeout)
            tokens = 0
            for line in done.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") == "turn.completed":
                    usage = event.get("usage") or {}
                    tokens += int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)
            text = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
            if not text or not tokens or LIMIT.search(done.stderr[-600:]):
                raise SystemExit(f"{family} call did not run (exit {done.returncode}): {done.stderr[-300:]}")
    return text, tokens, round(time.time() - started, 1)

MASK = TG.MASK
case_sources = TG.case_sources
PROMPT = TG.PROMPT.replace(
    '''Output ONLY JSON:''',
    '''- Separately list under "mentioned_only" each planted defect (C or M id) that the review raises only as an
  uncertainty, a question, a conditional risk, or a finding too vague or wrong to count as a detection; an id in
  "detected" is never also in "mentioned_only".

Output ONLY JSON:''').replace('''"hard_negatives_violated": ["H1", ...],''',
                              '''"hard_negatives_violated": ["H1", ...], "mentioned_only": ["M1", ...],''')
SALT = "x2-2026-11-08"
REQUIRED = {"valid_review": bool, "detected": list, "unsupported_claims": list, "hard_negatives_violated": list,
            "mentioned_only": list}


class NotGraded(Exception):
    """A grader answer that cannot be scored: never recorded as a grade (rerun resumes)."""


def check(verdict, ids=None):
    """Complete schema and known ids only: an unknown or malformed id is a failed grade, never a silent zero."""
    if not isinstance(verdict, dict):
        raise NotGraded("verdict is not an object")
    missing = [k for k, kind in REQUIRED.items() if not isinstance(verdict.get(k), kind)]
    if missing:
        raise NotGraded(f"verdict lacks {', '.join(missing)}")
    if ids is not None:
        planted = {rid for rid, group in ids.items() if group in ("critical", "major")}
        hard = {rid for rid, group in ids.items() if group == "hard_negatives"}
        for field, allowed in (("detected", planted), ("mentioned_only", planted), ("hard_negatives_violated", hard)):
            bad = [x for x in verdict[field] if not isinstance(x, str) or x not in allowed]
            if bad:
                raise NotGraded(f"{field} has ids outside the rubric: {bad[:5]}")
        if set(verdict["detected"]) & set(verdict["mentioned_only"]):
            raise NotGraded("an id is both detected and mentioned_only")
        if not all(isinstance(c, dict) and isinstance(c.get("claim"), str) and c["claim"].strip()
                   for c in verdict["unsupported_claims"]):
            raise NotGraded("each unsupported claim needs a non-empty claim")
    return verdict


def rubric_ids(spec, case):
    items = spec["rubric"][case]
    ids = [(f"C{i + 1}", "critical", i) for i in range(len(items.get("critical", [])))]
    ids += [(f"M{i + 1}", "major", i) for i in range(len(items.get("major", [])))]
    ids += [(f"H{i + 1}", "hard_negatives", i) for i in range(len(items.get("hard_negatives", [])))]
    return ids


def rubric_text(spec, case):
    items = spec["rubric"][case]
    lines = [f"{rid} ({group}): {items[group][index]}" for rid, group, index in rubric_ids(spec, case)]
    if not items.get("critical") and not items.get("major"):
        lines.insert(0, "This case has no planted defect (critical: none, major: none).")
    if items.get("no_double_credit"):
        lines.append("No double credit: " + items["no_double_credit"])
    return "\n".join(lines)


def anonymous(report):
    return TG.anonymous(report)


def summarize(spec, row, verdict):
    ids = {rid: group for rid, group, _i in rubric_ids(spec, row["id"])}
    detected = sorted({d for d in verdict.get("detected") or [] if ids.get(d) in ("critical", "major")})
    mentioned = sorted({d for d in verdict.get("mentioned_only") or [] if ids.get(d) in ("critical", "major")} - set(detected))
    violated = sorted({h for h in verdict.get("hard_negatives_violated") or [] if ids.get(h) == "hard_negatives"})
    return {"detected": detected, "mentioned_only": mentioned, "hard_negatives_violated": violated,
            "unsupported": len(verdict.get("unsupported_claims") or []), "valid": bool(verdict.get("valid_review")),
            "planted": sum(1 for g in ids.values() if g in ("critical", "major"))}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--rows", required=True)
    parser.add_argument("--family", choices=("opus", "codex", *CHEAP), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--claude", default="")
    parser.add_argument("--codex", default="")
    args = parser.parse_args(argv)
    spec = json.load(open(os.path.join(args.cases, "spec.json"), encoding="utf-8"))
    rows = [json.loads(l) for p in args.rows.split(",") for l in open(p, encoding="utf-8")]
    def row_key(r):  # calibration repeats carry |rN; single runs keep the original key
        return f"{r['cell']}|{r['arm']}|{r['id']}" + (f"|r{r['rep']}" if r.get("rep", 1) != 1 else "")
    rows.sort(key=lambda r: hashlib.sha256(f"{SALT}|{row_key(r)}".encode()).hexdigest())
    grader_sha = hashlib.sha256(b"".join(open(os.path.join(HERE, n), "rb").read() for n in ("x2_grade.py", "x2_case_tools.py"))
                                + PROMPT.encode()).hexdigest()
    spec_sha = hashlib.sha256(open(os.path.join(args.cases, "spec.json"), "rb").read()).hexdigest()
    done = set()
    if os.path.exists(args.out):
        for line in open(args.out, encoding="utf-8"):
            old = json.loads(line)
            if old.get("grader_sha256") != grader_sha or old.get("spec_sha256") != spec_sha:
                raise SystemExit(f"{args.out}: {old['key']} was graded by another grader or spec version; "
                                 "a mixed-version grade set is not allowed (PREREG)")
            if old["key"] in done:
                raise SystemExit(f"{args.out}: duplicate grade for {old['key']}")
            done.add(old["key"])
    seen_keys = set()
    for row in rows:
        key = row_key(row)
        if key in seen_keys:
            raise SystemExit(f"two rows share the identity {key}; refusing to grade")
        seen_keys.add(key)
        if key in done:
            continue
        report = row.get("report")
        if not isinstance(report, dict) or (report.get("findings") is None and report.get("uncertainties") is None):
            verdict, tokens = {"valid_review": False, "detected": [], "unsupported_claims": [],
                               "hard_negatives_violated": [], "mentioned_only": [], "note": "no parsable report"}, 0
        else:
            prompt = PROMPT.format(sources=case_sources(args.cases, row["id"]), rubric=rubric_text(spec, row["id"]),
                                   review=anonymous(report))
            grader = cheap_call if args.family in CHEAP else call
            try:
                text, tokens, _seconds = grader(args.family, prompt, args.claude, args.codex)
            except (SystemExit, subprocess.TimeoutExpired, ValueError, OSError) as exc:
                with open(args.out + ".deviations", "a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"key": key, "family": args.family, "tokens": None,
                                             "why": f"call did not run: {str(exc)[:300]}"}, ensure_ascii=False) + "\n")
                print(f"{args.family} {key}: grader call did not run; stopping, rerun to resume", flush=True)
                return 6
            try:
                verdict = check(parse(text), {rid: group for rid, group, _i in rubric_ids(spec, row["id"])})
            except (ValueError, NotGraded) as exc:
                with open(args.out + ".deviations", "a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"key": key, "family": args.family, "tokens": tokens, "why": str(exc),
                                             "raw": text[:1500]}, ensure_ascii=False) + "\n")
                print(f"{args.family} {key}: not graded ({exc}); stopping, rerun to resume", flush=True)
                return 6
        entry = {"key": key, "cell": row["cell"], "arm": row["arm"], "id": row["id"], "rep": row.get("rep", 1),
                 "grader_sha256": grader_sha, "spec_sha256": spec_sha,
                 "report_sha256": hashlib.sha256(json.dumps(row.get("report"), sort_keys=True).encode()).hexdigest(),
                 "row_runner_sha256": row.get("runner_sha256"),
                 "family": args.family,
                 "verdict": verdict, "tokens": tokens}
        entry.update(summarize(spec, row, verdict))
        with open(args.out, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"{args.family} graded {key}: detected {entry['detected']} unsupported {entry['unsupported']} "
              f"tokens {tokens:,}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
