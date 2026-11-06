"""Cross-family and repeat grading for V3, V4, V5, V6 and V8 of PREREG.md.

The prompt for each answer is built by the experiment's own frozen grader module (code map, EGM or court), word
for word, with the same masking. Only the model that reads it changes:
- backend "codex": `codex exec`, read-only sandbox, empty temporary folder, --ephemeral, --ignore-user-config;
- backend "claude": `claude -p`, no tools, empty temporary folder, same flags as the frozen graders.
`--order reversed` reverses the reference facts (code map, court) or the rubric items (EGM); this is the per-answer
counterpart of grading in both orders.

    python3 xgrade.py --kind codemap|egm|court --module <experiment taste_grade.py> --rows <rows.jsonl>
        --ref <questions.json | cases.json[,more.json] | egm-local folder> --out <grades.jsonl>
        --backend codex|claude [--model M] [--effort E] [--order original|reversed] [--workers 4]

A grade that did not run (usage limit, error, zero tokens, unparsable JSON) is never written as a score: it goes to
<out>.deviations and the driver stops with exit 6 once the running calls finish; rerunning resumes.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

CODEX = "/mnt/drugs/akuo/conda_envs/claude/bin/codex"
CLAUDE = "/mnt/drugs/akuo/conda_envs/claude/bin/claude"
LIMIT = re.compile(r"hit your (?:\w+ )?limit|usage limit|rate limit|too many requests|\b429\b|limit \W* resets", re.I)


class NotRun(Exception):
    pass


def load_module(path):
    spec = importlib.util.spec_from_file_location("frozen_grade_" + hashlib.sha256(path.encode()).hexdigest()[:8], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse(text):
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        raise NotRun("no JSON in the reply")
    try:
        return json.loads(match.group(0))
    except ValueError as exc:
        raise NotRun(f"malformed JSON ({exc})")


def call_codex(prompt, model, effort):
    with tempfile.TemporaryDirectory(prefix="xgrade-") as cwd:
        last = os.path.join(cwd, "last.txt")
        argv = [CODEX, "exec", "--sandbox", "read-only", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config",
                "-C", cwd, "-o", last, "--json"]
        if model:
            argv += ["-m", model]
        if effort:
            argv += ["-c", f"model_reasoning_effort={effort}"]
        env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "PATH": os.path.dirname(CODEX) + ":/usr/bin:/bin"}
        done = subprocess.run(argv + ["-"], input=prompt, cwd=cwd, env=env, capture_output=True, text=True, timeout=1200)
        text = open(last, encoding="utf-8").read() if os.path.exists(last) else ""
    tokens = 0
    for line in done.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "turn.completed":
            usage = event.get("usage") or {}
            tokens += sum(int(usage.get(k) or 0) for k in ("input_tokens", "output_tokens"))
        if event.get("type") in ("error", "turn.failed"):
            raise NotRun(json.dumps(event)[:160])
    if done.returncode != 0 or tokens == 0 or LIMIT.search(text[:300]):
        raise NotRun(f"exit {done.returncode}, tokens {tokens}: {(text or done.stderr)[-160:]}")
    return _parse(text), tokens


def call_claude(prompt, model, effort):
    env = {"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "PATH": os.path.dirname(CLAUDE) + ":/usr/bin:/bin"}
    with tempfile.TemporaryDirectory(prefix="xgrade-") as cwd:
        done = subprocess.run([CLAUDE, "-p", prompt, "--output-format", "json", "--tools", "", "--strict-mcp-config",
                               "--setting-sources", "project", "--no-session-persistence"]
                              + (["--model", model] if model else []) + (["--effort", effort] if effort else []),
                              cwd=cwd, env=env, capture_output=True, text=True, timeout=900, stdin=subprocess.DEVNULL)
    try:
        envelope = json.loads(done.stdout)
    except ValueError:
        raise NotRun(f"no JSON envelope (exit {done.returncode})")
    text = envelope.get("result", "") or ""
    usage = envelope.get("usage", {}) or {}
    tokens = sum(int(usage.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                                                   "cache_read_input_tokens"))
    if envelope.get("is_error") or LIMIT.search(text[:300]) or tokens == 0:
        raise NotRun(text[:160] or "error envelope")
    return _parse(text), tokens


class Codemap:
    def __init__(self, module, ref, order):
        self.m, self.order = module, order
        self.questions = {q["id"]: q for q in json.load(open(ref, encoding="utf-8"))["questions"]}

    def prompt(self, row):
        q = self.questions[row["id"]]
        facts = q["facts"][::-1] if self.order == "reversed" else q["facts"]
        text = "\n".join(f"{f['id']}: {f['fact']} [{f.get('where', '')}]{' (essential)' if f.get('essential') else ''}"
                         for f in facts)
        return self.m.PROMPT.format(question=q["question"], facts=text, answer=self.m.MASK.sub("[tool]", row["answer"])[:12000])

    def has_answer(self, row):
        return bool((row.get("answer") or "").strip())

    def empty(self):
        return {"facts": {}, "wrong_claims": None, "note": "no answer"}

    def item(self, row, verdict):
        facts = self.questions[row["id"]]["facts"]
        present = [f for f in facts if verdict.get("facts", {}).get(f["id"]) == "present"]
        essential = [f for f in facts if f.get("essential")]
        return {"coverage": round(len(present) / len(facts), 3) if facts else 0.0,
                "essential_ok": all(verdict.get("facts", {}).get(f["id"]) == "present" for f in essential),
                "contradicted": sum(1 for v in (verdict.get("facts") or {}).values() if v == "contradicted")}


class Court:
    def __init__(self, module, ref, order):
        self.m, self.order = module, order
        self.cases = {}
        for path in ref.split(","):
            for case in json.load(open(path, encoding="utf-8"))["cases"]:
                self.cases[case["id"]] = case

    def prompt(self, row):
        case = self.cases[row["id"]]
        facts = case["facts"][::-1] if self.order == "reversed" else case["facts"]
        alarms = case["false_alarms"][::-1] if self.order == "reversed" else case["false_alarms"]
        prompt = self.m.PROMPT.format(case=case["case"], facts="\n".join(f"{f['id']}: {f['fact']}" for f in facts),
                                      alarms="\n".join(f"{a['id']}: {a['objection']} | {a['answered_by']}" for a in alarms)
                                      or "(none)", answer=self.m.mask(row["answer"])[:20000])
        if case["expected_bottom_line"] == "conditional":
            prompt = prompt.replace('"none" if it\n  takes no position', '"conditional" if it\n  says go only under '
                                    'specific stated conditions or that it depends on missing facts; "none" if it\n  takes '
                                    'no position').replace('"bottom_line": "go|no-go|none"',
                                                           '"bottom_line": "go|no-go|conditional|none"')
        return prompt

    def has_answer(self, row):
        return bool((row.get("answer") or "").strip())

    def empty(self):
        return {"facts": {}, "false_alarms": {}, "bottom_line": "none", "wrong_claims": None, "note": "no answer"}

    def item(self, row, verdict):
        case = self.cases[row["id"]]
        facts = case["facts"]
        present = [f for f in facts if (verdict.get("facts") or {}).get(f["id"]) == "present"]
        essential = [f for f in facts if f.get("essential")]
        return {"coverage": round(len(present) / len(facts), 3) if facts else 0.0,
                "essential_ok": all((verdict.get("facts") or {}).get(f["id"]) == "present" for f in essential),
                "contradicted": sum(1 for v in (verdict.get("facts") or {}).values() if v == "contradicted"),
                "false_alarms_raised": sum(1 for v in (verdict.get("false_alarms") or {}).values() if v == "raised"),
                "bottom_line_ok": verdict.get("bottom_line") == case["expected_bottom_line"]}


class Egm:
    ID_LINE = re.compile(r"^[CMH]\d+ \(")

    def __init__(self, module, ref, order):
        self.m, self.order, self.cases_dir = module, order, ref
        self.spec = json.load(open(os.path.join(ref, "spec.json"), encoding="utf-8"))

    def prompt(self, row):
        rubric = self.m.rubric_text(self.spec, row["id"]).split("\n")
        if self.order == "reversed":
            slots = [i for i, line in enumerate(rubric) if self.ID_LINE.match(line)]
            items = [rubric[i] for i in slots][::-1]
            for i, line in zip(slots, items):
                rubric[i] = line
        return self.m.PROMPT.format(sources=self.m.case_sources(self.cases_dir, row["id"]), rubric="\n".join(rubric),
                                    review=self.m.anonymous(row["report"]))

    def has_answer(self, row):
        report = row.get("report")
        return isinstance(report, dict) and (report.get("findings") is not None or report.get("uncertainties") is not None)

    def empty(self):
        return {"valid_review": False, "detected": [], "unsupported_claims": [], "hard_negatives_violated": [],
                "valid_additional_findings": 0, "uncertainties": 0, "note": "no parsable report"}

    def item(self, row, verdict):
        ids = {rid: group for rid, group, _i in self.m.RUBRIC_IDS[row["id"]]}
        detected = sorted({d for d in verdict.get("detected") or [] if ids.get(d) in ("critical", "major")})
        return {"detected": detected, "critical": sum(1 for d in detected if ids[d] == "critical"),
                "major": sum(1 for d in detected if ids[d] == "major"),
                "unsupported": len(verdict.get("unsupported_claims") or []), "valid": bool(verdict.get("valid_review"))}


KINDS = {"codemap": Codemap, "court": Court, "egm": Egm}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=sorted(KINDS))
    parser.add_argument("--module", required=True)
    parser.add_argument("--rows", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--backend", required=True, choices=("codex", "claude"))
    parser.add_argument("--model", default="")
    parser.add_argument("--effort", default="")
    parser.add_argument("--order", default="original", choices=("original", "reversed"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--salt", default="xgrade", help="changes the hash-shuffled grading order")
    args = parser.parse_args(argv)
    kind = KINDS[args.kind](load_module(args.module), args.ref, args.order)
    rows = [json.loads(line) for line in open(args.rows, encoding="utf-8") if line.strip()]
    done = set()
    if os.path.exists(args.out):
        done = {json.loads(line)["key"] for line in open(args.out, encoding="utf-8") if line.strip()}
    todo = [r for r in sorted(rows, key=lambda r: hashlib.sha256(
        f"{args.salt}|{r['arm']}|{r['id']}|{r['rep']}".encode()).hexdigest()) if f"{r['arm']}|{r['id']}|{r['rep']}" not in done]
    call = call_codex if args.backend == "codex" else call_claude
    lock, stop = threading.Lock(), threading.Event()

    def work(row):
        if stop.is_set():
            return
        key = f"{row['arm']}|{row['id']}|{row['rep']}"
        tokens = 0
        if kind.has_answer(row):
            try:
                verdict, tokens = call(kind.prompt(row), args.model, args.effort)
            except NotRun as exc:
                stop.set()
                with lock, open(args.out + ".deviations", "a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"key": key, "backend": args.backend, "reason": str(exc)}) + "\n")
                print(f"not run {key}: {exc}", flush=True)
                return
        else:
            verdict = kind.empty()
        verdict["_grader_tokens"] = tokens
        item = {"key": key, "arm": row["arm"], "id": row["id"], "rep": row["rep"], "verdict": verdict,
                **kind.item(row, verdict),
                "_grader": {"backend": args.backend, "model": args.model or "default", "effort": args.effort or "default",
                            "order": args.order}}
        with lock, open(args.out, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"graded {key}", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, todo))
    return 6 if stop.is_set() else 0


if __name__ == "__main__":
    sys.exit(main())
