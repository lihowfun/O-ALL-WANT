#!/usr/bin/env python3
"""Score code-location arms on the frozen code-map question set (Stage 0-alpha, D24).

  score.py corpus-hash CORPUS
      Print the corpus file count, file-list hash and content hash.
  score.py check --questions Q --corpus CORPUS
      Validate the question file against the corpus (gold files exist, class-a
      symbols span the recorded lines, question texts do not name their targets).
  score.py run --questions Q --corpus CORPUS --arm NAME=TEMPLATE [--arm ...] --out DIR
      Run every question once per arm and write results.json and results.md. The
      corpus file list must match the frozen one, and the questions' sha256 must
      match the one recorded in the PREREG.md beside them (or --prereg).

An arm is a command template run as a subprocess with cwd = a fresh copy of the
corpus, once in text mode (output bytes, wall time) and once in JSON mode (the
ranking). Placeholders: {sub} the subcommand, {args} its arguments (expands to
several argv items), {json} where the JSON flag goes (appended as --json when
absent), {python} this interpreter, {repo} this repository, {corpus} the arm's
corpus copy. The scorer never imports an arm. Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

SCHEMA_VERSION = 1
REPO = Path(__file__).resolve().parents[2]
CLASSES = ("a", "b", "c", "d")
CLASS_NAMES = {"a": "concept -> definition", "b": "callers", "c": "change impact (git history)", "d": "module path"}
SUBCOMMANDS = {"a": "find", "b": "callers", "c": "find", "d": "path"}
TOP_K = 5
RANK_CUTOFF = 10
PASS_DELTA = 0.15
EPSILON = 1e-9
GENERATED_PREFIX = "example/"
DEFAULT_TIMEOUT = 300


class ScoreError(ValueError):
    pass


# --------------------------------------------------------------------------- corpus

def corpus_files(corpus: Path) -> list[str]:
    files = []
    for directory, dirnames, filenames in os.walk(corpus):
        dirnames.sort()
        for name in filenames:
            path = Path(directory) / name
            if path.is_file() and not path.is_symlink():
                files.append(path.relative_to(corpus).as_posix())
    return sorted(files)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def corpus_identity(corpus: Path) -> dict:
    """file_list_sha256 hashes the sorted relative POSIX paths, one per line with a trailing LF;
    content_sha256 hashes "sha256(bytes)  path" lines in the same order."""
    files = corpus_files(corpus)
    listing = "".join(path + "\n" for path in files).encode("utf-8")
    contents = "".join(f"{sha256_bytes((corpus / path).read_bytes())}  {path}\n" for path in files).encode("utf-8")
    return {"files": len(files), "file_list_sha256": sha256_bytes(listing), "content_sha256": sha256_bytes(contents)}


def generated_twins(corpus: Path) -> dict[str, set[str]]:
    """Each file under example/ -> the files outside example/ with identical bytes (its generated sources)."""
    by_hash: dict[str, list[str]] = {}
    for path in corpus_files(corpus):
        by_hash.setdefault(sha256_bytes((corpus / path).read_bytes()), []).append(path)
    twins = {}
    for paths in by_hash.values():
        sources = {path for path in paths if not path.startswith(GENERATED_PREFIX)}
        for path in paths:
            if path.startswith(GENERATED_PREFIX) and sources:
                twins[path] = sources
    return twins


# --------------------------------------------------------------------------- questions

def load_questions(path: Path) -> tuple[dict, str]:
    data = path.read_bytes()
    document = json.loads(data.decode("utf-8"))
    if document.get("schema_version") != SCHEMA_VERSION or not isinstance(document.get("questions"), list):
        raise ScoreError("questions file must have schema_version 1 and a questions list")
    return document, sha256_bytes(data)


def prereg_status(prereg: Path | None, questions_sha: str) -> str:
    if prereg is None:
        return "not checked"
    text = prereg.read_text(encoding="utf-8")
    recorded = re.findall(r"questions\.json sha256:\s*`?([0-9a-f]{64})`?", text)
    if not recorded:
        raise ScoreError(f"{prereg} records no 'questions.json sha256:' line")
    if questions_sha not in recorded:
        raise ScoreError(f"questions.json sha256 {questions_sha} differs from the one recorded in {prereg}")
    return "matches PREREG"


def symbol_span(source: str, symbol: str) -> tuple[int, int] | None:
    """(first, last) line of a module-level `name` or `Class.method` definition."""
    body = ast.parse(source).body
    node = None
    for part in symbol.split("."):
        node = next((item for item in body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                     and item.name == part), None)
        if node is None:
            return None
        body = node.body
    return node.lineno, node.end_lineno


def forbidden_names(question: dict) -> set[str]:
    """Names the question text must not contain (case-insensitive substring)."""
    names = set()
    gold = question["gold"]
    files = list(gold["files"])
    for path in files:
        pure = PurePosixPath(path)
        names.add(pure.name.casefold())
        if len(pure.stem) >= 4:
            names.add(pure.stem.casefold())
    if question["class"] == "a":
        for part in gold["symbol"].split("."):
            names.add(part.lstrip("_").casefold())
    return names


def check_questions(document: dict, corpus: Path) -> list[str]:
    problems = []
    files = set(corpus_files(corpus))
    seen = set()
    counts = {name: 0 for name in CLASSES}
    for question in document["questions"]:
        qid = question.get("id")
        where = f"{qid}:"
        if not qid or qid in seen:
            problems.append(f"{where} missing or duplicate id")
        seen.add(qid)
        kind = question.get("class")
        if kind not in CLASSES:
            problems.append(f"{where} unknown class {kind!r}")
            continue
        counts[kind] += 1
        missing = [field for field in ("text", "command", "gold", "gold_method", "difficulty") if not question.get(field)]
        if missing:
            problems.append(f"{where} missing {', '.join(missing)}")
            continue
        command, gold = question["command"], question["gold"]
        if command.get("sub") != SUBCOMMANDS[kind]:
            problems.append(f"{where} class {kind} must use {SUBCOMMANDS[kind]}")
        if not gold.get("files") or len(set(gold["files"])) != len(gold["files"]):
            problems.append(f"{where} gold.files must be a non-empty list without duplicates")
        for path in gold.get("files", []):
            if path not in files:
                problems.append(f"{where} gold file not in corpus: {path}")
            if path.startswith(GENERATED_PREFIX):
                problems.append(f"{where} gold file is a generated copy: {path}")
        if kind in ("a", "c") and command.get("args") != [question["text"]]:
            problems.append(f"{where} find must receive the question text")
        if kind == "a":
            path = gold["files"][0]
            if len(gold["files"]) != 1 or not gold.get("symbol") or len(gold.get("lines", [])) != 2:
                problems.append(f"{where} class a needs one file, a symbol and [first, last] lines")
            elif path in files and path.endswith(".py"):
                span = symbol_span((corpus / path).read_text(encoding="utf-8"), gold["symbol"])
                if span != tuple(gold["lines"]):
                    problems.append(f"{where} {path}::{gold['symbol']} spans {span}, not {gold['lines']}")
        if kind == "b":
            symbol = command.get("args", [""])[0]
            defined = gold.get("defined_in", "")
            if defined not in files or symbol_span((corpus / defined).read_text(encoding="utf-8"), symbol) is None:
                problems.append(f"{where} {symbol} is not defined in {defined}")
        if kind == "c" and not re.fullmatch(r"[0-9a-f]{40}", gold.get("commit", "")):
            problems.append(f"{where} class c needs the full commit hash")
        if kind == "d":
            args = command.get("args", [])
            chains = gold.get("chains", [])
            middle = sorted({path for chain in chains for path in chain[1:-1]})
            if len(args) != 2 or any(arg not in files for arg in args):
                problems.append(f"{where} path needs two corpus files")
            elif not chains or any(chain[0] != args[0] or chain[-1] != args[1] or len(chain) < 3 for chain in chains):
                problems.append(f"{where} chains must run from args[0] to args[1] through at least one module")
            if middle != sorted(gold["files"]):
                problems.append(f"{where} gold.files must be the chains' intermediate modules")
        text = question["text"].casefold()
        if kind in ("b", "d"):  # the queried symbol and the two endpoints are given by design
            for given in command.get("args", []):
                text = text.replace(given.casefold(), " ")
        for name in sorted(forbidden_names(question)):
            if name and name in text:
                problems.append(f"{where} question text names its target ({name})")
    for kind, (low, high) in {"a": (8, 12), "b": (6, 10), "c": (10, 14), "d": (4, 6)}.items():
        if not low <= counts[kind] <= high:
            problems.append(f"class {kind}: {counts[kind]} questions, expected {low}-{high}")
    return problems


# --------------------------------------------------------------------------- arms

def parse_arm(value: str) -> tuple[str, str]:
    name, separator, template = value.partition("=")
    if not separator or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name) or not template.strip():
        raise ScoreError(f"arm must look like NAME=TEMPLATE: {value!r}")
    return name, template


def expand(template: str, *, sub: str | None, args: list[str], json_mode: bool, workdir: Path) -> list[str]:
    values = {"{python}": sys.executable, "{repo}": REPO.as_posix(), "{corpus}": workdir.as_posix()}
    argv, placed_json = [], False
    for token in shlex.split(template):
        if token == "{args}":
            argv.extend(args)
        elif token == "{json}":
            placed_json = True
            argv.extend(["--json"] if json_mode else [])
        elif token == "{sub}":
            if sub is not None:
                argv.append(sub)
        else:
            for key, value in values.items():
                token = token.replace(key, value)
            argv.append(token)
    if json_mode and not placed_json:
        argv.append("--json")
    return argv


def template_files(template: str, workdir: Path) -> dict:
    """sha256 of every existing file the template names (the arm's code as it was run)."""
    found = {}
    for token in expand(template, sub=None, args=[], json_mode=False, workdir=workdir):
        path = Path(token) if Path(token).is_absolute() else workdir / token
        if path.is_file() and Path(token).suffix:
            found[token] = sha256_bytes(path.read_bytes())
    return found


def arm_environment() -> dict:
    environment = os.environ.copy()
    environment.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    return environment


def invoke(argv: list[str], workdir: Path, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        process = subprocess.run(argv, cwd=workdir, env=arm_environment(), capture_output=True, timeout=timeout)
        code, stdout, stderr = process.returncode, process.stdout, process.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = "timeout", exc.stdout or b"", exc.stderr or b""
    except OSError as exc:
        code, stdout, stderr = "not started", b"", str(exc).encode("utf-8", "replace")
    seconds = time.perf_counter() - started
    stdout = stdout.replace(b"\r\n", b"\n")  # Windows text-mode newlines are not output size
    return {"exit": code, "stdout": stdout, "stderr": stderr.decode("utf-8", "replace")[-2000:], "seconds": seconds}


def normalize_path(value, workdir: Path) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().split("::", 1)[0]
    candidate = Path(text)
    if candidate.is_absolute():
        try:
            text = candidate.resolve().relative_to(workdir.resolve()).as_posix()
        except (OSError, ValueError):
            return text.replace("\\", "/")
    text = text.replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    text = re.sub(r":\d+(?::\d+)?$", "", text)
    return text


def ranked_paths(payload, workdir: Path) -> tuple[list[str], list, str | None]:
    """Result paths in arm order and their `line` values; an error string for unusable JSON."""
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        return [], [], "JSON output has no results list"
    paths, lines = [], []
    for item in payload["results"]:
        path = normalize_path(item.get("path") if isinstance(item, dict) else None, workdir)
        if path is not None:
            paths.append(path)
            lines.append(item.get("line"))
    return paths, lines, None


# --------------------------------------------------------------------------- metrics

def canonical(path: str, gold: set[str], twins: dict[str, set[str]]) -> str:
    sources = twins.get(path)
    if not sources:
        return path
    matching = sorted(sources & gold)
    return matching[0] if matching else min(sources)


def score_question(question: dict, paths: list[str], lines: list, twins: dict[str, set[str]]) -> dict:
    gold = set(question["gold"]["files"])
    ordered, first_line = [], {}
    for path, line in zip(paths, lines):
        name = canonical(path, gold, twins)
        if name not in first_line:
            first_line[name] = line
            ordered.append(name)
    if question["class"] == "d":
        endpoints = {canonical(path, gold, twins) for path in question["command"]["args"]}
        ordered = [path for path in ordered if path not in endpoints]
    top = ordered[:RANK_CUTOFF]
    rank = next((index + 1 for index, path in enumerate(top) if path in gold), None)
    found = [path for path in top if path in gold]
    result = {"ranked": top, "hit1": bool(top) and top[0] in gold, "hit5": any(path in gold for path in top[:TOP_K]),
              "rr": 1 / rank if rank else 0.0, "precision": len(found) / len(top) if top else 0.0,
              "recall": len(found) / len(gold)}
    if question["class"] == "a":
        first, last = question["gold"]["lines"]
        line = first_line.get(top[0]) if top else None
        try:
            line = int(line)
        except (TypeError, ValueError):
            line = None
        result["line_hit1"] = bool(result["hit1"] and line is not None and first <= line <= last)
    return result


def summarize(rows: list[dict]) -> dict:
    summary = {}
    for kind in CLASSES:
        selected = [row for row in rows if row["class"] == kind]
        if not selected:
            continue
        mean = lambda key: round(statistics.fmean(row[key] for row in selected), 4)  # noqa: E731
        entry = {"n": len(selected), "top1": mean("hit1"), "top5": mean("hit5"), "mrr": mean("rr"),
                 "text_bytes": sum(row["text_bytes"] for row in selected),
                 "median_text_bytes": statistics.median(row["text_bytes"] for row in selected),
                 "seconds": round(sum(row["seconds"] for row in selected), 3),
                 "median_seconds": round(statistics.median(row["seconds"] for row in selected), 3),
                 "errors": sum(bool(row["error"]) for row in selected)}
        if kind in ("b", "c"):
            entry["precision"], entry["recall"] = mean("precision"), mean("recall")
        if kind == "a":
            entry["line_top1"] = mean("line_hit1")
        summary[kind] = entry
    return summary


def gate(summary: dict, baseline: str, partial: bool) -> dict:
    """D24: some class where the arm's top-5 file hit rate beats the baseline by >= 0.15
    while its text output bytes in that class are not more than the baseline's."""
    if partial:
        return {"evaluated": False, "reason": "partial run (--ids); the pre-registered rule needs every question"}
    if baseline not in summary:
        return {"evaluated": False, "reason": f"baseline arm {baseline} was not run"}
    verdicts = {}
    for arm, classes in summary.items():
        if arm == baseline:
            continue
        rows = {}
        for kind, entry in classes.items():
            base = summary[baseline].get(kind)
            if base is None:
                continue
            delta = round(entry["top5"] - base["top5"], 4)
            fewer_bytes = entry["text_bytes"] <= base["text_bytes"]
            rows[kind] = {"top5_delta": delta, "text_bytes": entry["text_bytes"], "baseline_text_bytes": base["text_bytes"],
                          "passes": delta >= PASS_DELTA - EPSILON and fewer_bytes}
        passing = [kind for kind, value in rows.items() if value["passes"]]
        verdicts[arm] = {"classes": rows, "passing_classes": passing, "pass": bool(passing)}
    return {"evaluated": True, "baseline": baseline, "rule": f"top5 delta >= {PASS_DELTA} and text bytes <= baseline in one class",
            "arms": verdicts}


# --------------------------------------------------------------------------- run

def run(args) -> int:
    questions_path, corpus = Path(args.questions).resolve(), Path(args.corpus).resolve()
    document, questions_sha = load_questions(questions_path)
    sibling = questions_path.parent / "PREREG.md"
    prereg = prereg_status(Path(args.prereg) if args.prereg else sibling if sibling.is_file() else None, questions_sha)
    identity = corpus_identity(corpus)
    expected = document.get("corpus", {}).get("file_list_sha256")
    if expected != identity["file_list_sha256"] and not args.allow_corpus_mismatch:
        raise ScoreError(f"corpus file list {identity['file_list_sha256']} differs from the frozen {expected}")
    arms = dict(parse_arm(value) for value in args.arm)
    setups = dict(parse_arm(value) for value in args.setup)
    if set(setups) - set(arms):
        raise ScoreError("--setup names an arm that is not run")
    selected = document["questions"]
    if args.ids:
        wanted = [item.strip() for item in args.ids.split(",") if item.strip()]
        unknown = set(wanted) - {question["id"] for question in selected}
        if unknown:
            raise ScoreError(f"unknown question ids: {', '.join(sorted(unknown))}")
        selected = [question for question in selected if question["id"] in wanted]
    twins = generated_twins(corpus)
    rows, arm_info = [], {}
    with tempfile.TemporaryDirectory(prefix="codemap-score-") as temporary:
        for arm, template in arms.items():
            workdir = Path(temporary) / arm / "corpus"
            shutil.copytree(corpus, workdir, symlinks=True)
            info = {"template": template, "files_sha256": template_files(template, workdir)}
            if arm in setups:
                setup = invoke(expand(setups[arm], sub=None, args=[], json_mode=False, workdir=workdir), workdir, args.timeout)
                info["setup"] = {"template": setups[arm], "exit": setup["exit"], "seconds": round(setup["seconds"], 3),
                                 "stderr": setup["stderr"] if setup["exit"] != 0 else ""}
                if setup["exit"] != 0:
                    raise ScoreError(f"setup for arm {arm} failed: {setup['exit']}\n{setup['stderr']}")
            arm_info[arm] = info
            for question in selected:
                command = question["command"]
                text_run = invoke(expand(template, sub=command["sub"], args=command["args"], json_mode=False, workdir=workdir),
                                  workdir, args.timeout)
                json_run = invoke(expand(template, sub=command["sub"], args=command["args"], json_mode=True, workdir=workdir),
                                  workdir, args.timeout)
                error = None
                try:
                    paths, lines, error = ranked_paths(json.loads(json_run["stdout"].decode("utf-8")), workdir)
                except (UnicodeError, ValueError):
                    paths, lines, error = [], [], "JSON output is not valid JSON"
                if text_run["exit"] != 0 or json_run["exit"] != 0:
                    error = f"exit text={text_run['exit']} json={json_run['exit']}: {(json_run['stderr'] or text_run['stderr']).strip()[-300:]}"
                metrics = score_question(question, paths, lines, twins)
                rows.append({"arm": arm, "id": question["id"], "class": question["class"], **metrics,
                             "text_bytes": len(text_run["stdout"]), "json_bytes": len(json_run["stdout"]),
                             "seconds": round(text_run["seconds"], 4), "json_seconds": round(json_run["seconds"], 4),
                             "error": error})
    summary = {arm: summarize([row for row in rows if row["arm"] == arm]) for arm in arms}
    partial = len(selected) != len(document["questions"])
    report = {"schema_version": SCHEMA_VERSION, "questions": questions_path.name, "questions_sha256": questions_sha,
              "prereg": prereg, "corpus": {**identity, "commit": document.get("corpus", {}).get("commit")},
              "partial": partial, "question_ids": [question["id"] for question in selected],
              "harness_sha256": {name: sha256_bytes((Path(__file__).parent / name).read_bytes())
                                 for name in ("score.py", "native_search.py")},
              "top_k": TOP_K, "rank_cutoff": RANK_CUTOFF, "arms": arm_info, "summary": summary,
              "gate": gate(summary, args.baseline, partial), "rows": rows,
              "platform": {"python": sys.version.split()[0], "os": sys.platform}}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown = render_markdown(report)
    (out / "results.md").write_text(markdown, encoding="utf-8")
    sys.stdout.write(markdown)
    return 0


def render_markdown(report: dict) -> str:
    lines = [f"# Code-map scores ({'partial: harness check only' if report['partial'] else 'full run'})", "",
             f"- questions: {report['questions']} sha256 `{report['questions_sha256']}` ({report['prereg']})",
             f"- corpus: commit {report['corpus']['commit']}, {report['corpus']['files']} files, "
             f"file list `{report['corpus']['file_list_sha256']}`",
             f"- questions run: {len(report['question_ids'])}; top-k {report['top_k']}; MRR and precision/recall over the "
             f"first {report['rank_cutoff']} distinct files", "",
             "| arm | class | n | top-1 | top-5 | MRR | P@10 | R@10 | text bytes | seconds | errors |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, classes in report["summary"].items():
        for kind, entry in classes.items():
            precision = f"{entry['precision']:.3f}" if "precision" in entry else "-"
            recall = f"{entry['recall']:.3f}" if "recall" in entry else "-"
            lines.append(f"| {arm} | {kind} ({CLASS_NAMES[kind]}) | {entry['n']} | {entry['top1']:.3f} | {entry['top5']:.3f} | "
                         f"{entry['mrr']:.3f} | {precision} | {recall} | {entry['text_bytes']} | {entry['seconds']:.2f} | "
                         f"{entry['errors']} |")
    result = report["gate"]
    lines.append("")
    if not result["evaluated"]:
        lines.append(f"Gate not evaluated: {result['reason']}.")
    else:
        for arm, verdict in result["arms"].items():
            passing = ", ".join(verdict["passing_classes"]) or "none"
            lines.append(f"Gate for {arm} vs {result['baseline']}: {'PASS' if verdict['pass'] else 'FAIL'} "
                         f"(passing classes: {passing}; {result['rule']}).")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    identity = commands.add_parser("corpus-hash", help="print the corpus identity")
    identity.add_argument("corpus")
    check = commands.add_parser("check", help="validate questions against the corpus")
    check.add_argument("--questions", required=True)
    check.add_argument("--corpus", required=True)
    scoring = commands.add_parser("run", help="run arms and score them")
    scoring.add_argument("--questions", required=True)
    scoring.add_argument("--corpus", required=True)
    scoring.add_argument("--arm", action="append", required=True, help="NAME=TEMPLATE; repeat for each arm")
    scoring.add_argument("--setup", action="append", default=[], help="NAME=TEMPLATE run once in the arm's corpus copy first")
    scoring.add_argument("--baseline", default="R")
    scoring.add_argument("--ids", help="comma-separated question ids (a partial run never evaluates the gate)")
    scoring.add_argument("--prereg", help="PREREG.md whose recorded questions.json sha256 must match")
    scoring.add_argument("--allow-corpus-mismatch", action="store_true")
    scoring.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    scoring.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "corpus-hash":
            print(json.dumps(corpus_identity(Path(args.corpus).resolve()), indent=2))
            return 0
        if args.command == "check":
            document, digest = load_questions(Path(args.questions))
            problems = check_questions(document, Path(args.corpus).resolve())
            for problem in problems:
                print(problem)
            counts = {kind: sum(q.get("class") == kind for q in document["questions"]) for kind in CLASSES}
            print(f"{'FAIL' if problems else 'OK'}: {len(document['questions'])} questions {counts}; sha256 {digest}")
            return 1 if problems else 0
        return run(args)
    except (OSError, ScoreError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
