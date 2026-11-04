#!/usr/bin/env python3
"""Arm R of the code-map Stage 0-alpha evaluation: a simulated first native search.

It approximates what an agent sees after its first ripgrep-style search, with no
index and no cache: every run reads the files under --root (default: the
current directory) again.

  find "<text>"           keywords from the text (stop words dropped, snake and
                          camel case split, quoted names kept whole), searched
                          case-insensitively as substrings; files ranked by
                          IDF-weighted hit counts, one best line per file.
  callers <symbol>        whole-word matches of the symbol's last name part,
                          definition lines dropped; lines that look like a call
                          count 1, other mentions 0.25.
  path <A> <B>            two greps: the imports of A, and the files whose import
                          lines name B; reports A -> X -> B chains (or A -> B).
  affected <path[::Sym]>  files whose import lines name the module, the callers of
                          Sym when given, and files that mention the file name.

Text output is one line per file (`path:line: text`); --json prints
{"schema_version": 1, "results": [{"path", "score", "line"}]}. Standard library
only; it never imports or runs the searched files.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sys

SCHEMA_VERSION = 1
DEFAULT_LIMIT = 10
MAX_FILE_BYTES = 4 * 1024 * 1024
SNIPPET_CHARS = 120
SKIP_DIRS = frozenset({".git", ".hg", ".svn", "__pycache__", "node_modules"})
CALL_WEIGHT, MENTION_WEIGHT = 1.0, 0.25

# English function words plus the words a location question is phrased with; an
# agent would not grep for them.
STOP_WORDS = frozenset("""
a about above after again against all also am an and any are as at be because been before being below between both
but by can could did do does doing done down during each either else even ever every few for from further get gets
had has have having he her here hers him his how however i if in into is it its itself just less let lets like may
me might more most much must my need needs no nor not now of off on once one only onto or other others otherwise
our out over own per rather same shall she should since so some such than that the their them themselves then
there these they this those though through thus to too under until up upon us very via was we were what whatever
when whenever where wherever whether which while who whom whose why will with within without would yet you your
code codes function functions method methods file files module modules defined define defines definition
implemented implement implements implementation logic responsible handle handles handled use uses used using
find finds found locate located place part parts something thing things way ways given happen happens
""".split())

QUOTED = re.compile(r'"([^"\n]{2,}?)"|(?<!\w)\'([^\'\n]{2,}?)\'(?!\w)|`([^`\n]{2,}?)`')
WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]*|[0-9]+[A-Za-z_][A-Za-z0-9_]*")
CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")
IMPORT_LINE = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import\b|import\s+([\w.]+(?:\s+as\s+\w+)?(?:\s*,\s*[\w.]+(?:\s+as\s+\w+)?)*))")


def keywords(text: str) -> list[str]:
    """Search terms of a question, lowercased, in first-seen order."""
    terms: list[str] = []

    def add(term: str) -> None:
        term = term.strip().lower()
        if len(term) >= 3 and term not in STOP_WORDS and term not in terms:
            terms.append(term)

    for match in QUOTED.finditer(text):
        add(next(group for group in match.groups() if group is not None))
    rest = QUOTED.sub(" ", text)
    for token in WORD.findall(rest):
        parts = [piece for part in token.split("_") for piece in CAMEL.findall(part)]
        if len(parts) > 1:
            add(token)
        for part in parts or [token]:
            add(part)
    return terms


class Corpus:
    """All readable text files under root, read once per process."""

    def __init__(self, root: Path):
        self.root = root
        self.files: dict[str, list[str]] = {}
        for directory, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
            for name in sorted(filenames):
                path = Path(directory) / name
                try:
                    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
                        continue
                    data = path.read_bytes()
                except OSError:
                    continue
                if b"\0" in data[:8192]:
                    continue  # binary, as ripgrep skips it by default
                relative = path.relative_to(root).as_posix()
                self.files[relative] = data.decode("utf-8", "replace").splitlines()
        self._lower: dict[str, list[str]] = {}

    def lower(self, path: str) -> list[str]:
        if path not in self._lower:
            self._lower[path] = [line.lower() for line in self.files[path]]
        return self._lower[path]

    def python_files(self) -> list[str]:
        return [path for path in self.files if path.endswith(".py")]


def row(path: str, score: float, line: int, text: str) -> dict:
    return {"path": path, "score": round(score, 4), "line": line, "text": text}


def ranked(rows: list[dict], limit: int) -> list[dict]:
    return sorted(rows, key=lambda item: (-item["score"], item["path"]))[:limit]


def find(corpus: Corpus, text: str, limit: int) -> tuple[list[dict], list[str]]:
    terms = keywords(text)
    hits: dict[str, dict[str, list[int]]] = {}
    for path in corpus.files:
        lines = corpus.lower(path)
        found = {term: [number for number, line in enumerate(lines) if term in line] for term in terms}
        found = {term: numbers for term, numbers in found.items() if numbers}
        if found:
            hits[path] = found
    total = max(len(corpus.files), 1)
    frequency = {term: sum(term in found for found in hits.values()) for term in terms}
    idf = {term: math.log(1 + total / frequency[term]) for term in terms if frequency[term]}
    rows = []
    for path, found in hits.items():
        score = sum(idf[term] * (1 + math.log(len(numbers))) for term, numbers in found.items())
        per_line: dict[int, float] = {}
        for term, numbers in found.items():
            for number in numbers:
                per_line[number] = per_line.get(number, 0.0) + idf[term]
        best = min(per_line, key=lambda number: (-per_line[number], number))
        rows.append(row(path, score, best + 1, corpus.files[path][best]))
    return ranked(rows, limit), terms


def symbol_name(symbol: str) -> str:
    return re.split(r"::|\.", symbol.strip())[-1]


def callers(corpus: Corpus, symbol: str, limit: int, *, exclude=()) -> list[dict]:
    name = symbol_name(symbol)
    if not re.fullmatch(r"[A-Za-z_]\w*", name):
        return []
    word = re.compile(rf"(?<!\w){re.escape(name)}(?!\w)")
    definition = re.compile(rf"^\s*(?:async\s+def|def|class|function)\s+{re.escape(name)}(?!\w)")
    call = re.compile(rf"(?<!\w){re.escape(name)}\s*\(")
    rows = []
    for path, lines in corpus.files.items():
        if path in exclude:
            continue
        calls, mentions, first_call, first_mention = 0, 0, None, None
        for number, line in enumerate(lines):
            if not word.search(line) or definition.match(line):
                continue
            if call.search(line):
                calls += 1
                first_call = number if first_call is None else first_call
            else:
                mentions += 1
                first_mention = number if first_mention is None else first_mention
        if calls or mentions:
            best = first_call if first_call is not None else first_mention
            rows.append(row(path, calls * CALL_WEIGHT + mentions * MENTION_WEIGHT, best + 1, lines[best]))
    return ranked(rows, limit)


def resolve_module(corpus: Corpus, module: str, near: str | None) -> str | None:
    """The corpus file a module name most likely refers to: same folder first, then the shortest path."""
    relative = module.replace(".", "/") + ".py"
    if near is not None:
        local = PurePosixPath(near).parent / relative
        if local.as_posix() in corpus.files:
            return local.as_posix()
    tail = "/" + relative
    matches = [path for path in corpus.python_files() if path == relative or path.endswith(tail)]
    return min(matches, key=lambda path: (path.count("/"), path)) if matches else None


def imports_of(corpus: Corpus, path: str) -> list[tuple[str, int, str]]:
    """(file, line number, line) for each import line of path that resolves to a corpus file."""
    found, seen = [], set()
    for number, line in enumerate(corpus.files.get(path, [])):
        match = IMPORT_LINE.match(line)
        if not match:
            continue
        names = [match.group(1)] if match.group(1) else [item.split()[0] for item in match.group(2).split(",")]
        for name in names:
            target = resolve_module(corpus, name, path)
            if target and target != path and target not in seen:
                seen.add(target)
                found.append((target, number + 1, line))
    return found


def importers_of(corpus: Corpus, target: str) -> list[tuple[str, int, str]]:
    """(file, line number, line) for each Python file with an import line that resolves to target."""
    stem = PurePosixPath(target).stem
    pattern = re.compile(rf"^\s*(?:from\s+(?:[\w.]*\.)?{re.escape(stem)}\s+import\b|import\s+.*(?<![\w.]){re.escape(stem)}(?!\w))")
    found = []
    for path in corpus.python_files():
        if path == target:
            continue
        for number, line in enumerate(corpus.files[path]):
            if pattern.match(line) and any(item[0] == target for item in imports_of_line(corpus, path, line)):
                found.append((path, number + 1, line))
                break
    return found


def imports_of_line(corpus: Corpus, path: str, line: str) -> list[tuple[str, int, str]]:
    match = IMPORT_LINE.match(line)
    if not match:
        return []
    names = [match.group(1)] if match.group(1) else [item.split()[0] for item in match.group(2).split(",")]
    return [(target, 0, line) for target in (resolve_module(corpus, name, path) for name in names) if target]


def locate(corpus: Corpus, value: str) -> str | None:
    value = value.strip().replace("\\", "/").removeprefix("./")
    if value in corpus.files:
        return value
    module = value[:-3] if value.endswith(".py") else value
    return resolve_module(corpus, module, None)


def module_path(corpus: Corpus, start: str, goal: str, limit: int) -> tuple[list[dict], list[str]]:
    source, target = locate(corpus, start), locate(corpus, goal)
    if source is None or target is None:
        missing = start if source is None else goal
        return [], [f"no file found for {missing!r}"]
    outgoing = imports_of(corpus, source)
    incoming = importers_of(corpus, target)
    direct = next((item for item in outgoing if item[0] == target), None)
    if direct:
        rows = [row(source, 2.0, direct[1], direct[2]), row(target, 1.0, 1, corpus.files[target][0] if corpus.files[target] else "")]
        return rows, [f"{source} -> {target}"]
    into_target = {path: (number, line) for path, number, line in incoming}
    middle = [(path, number, line) for path, number, line in outgoing if path in into_target]
    if middle:
        rows = [row(source, 3.0, middle[0][1], middle[0][2])]
        rows += [row(path, 2.0, into_target[path][0], into_target[path][1]) for path, _number, _line in middle]
        rows.append(row(target, 1.0, 1, corpus.files[target][0] if corpus.files[target] else ""))
        return rows[:limit], [f"{source} -> {path} -> {target}" for path, _number, _line in middle]
    rows = [row(path, 0.5, number, line) for path, number, line in outgoing]
    rows += [row(path, 0.4, number, line) for path, number, line in incoming if path not in {r["path"] for r in rows}]
    return rows[:limit], [f"no import chain from {source} to {target} within two greps; candidates follow"]


def affected(corpus: Corpus, target: str, limit: int) -> tuple[list[dict], list[str]]:
    file_part, _, symbol = target.partition("::")
    seed = locate(corpus, file_part)
    if seed is None:
        return [], [f"no file found for {file_part!r}"]
    scores: dict[str, dict] = {}

    def merge(item: dict) -> None:
        current = scores.get(item["path"])
        if current is None:
            scores[item["path"]] = dict(item)
        else:
            current["score"] = round(current["score"] + item["score"], 4)

    for path, number, line in importers_of(corpus, seed):
        merge(row(path, 2.0, number, line))
    if symbol:
        for item in callers(corpus, symbol, len(corpus.files), exclude={seed}):
            merge(item)
    name = PurePosixPath(seed).name
    mention = re.compile(rf"(?<![\w.-]){re.escape(name)}(?![\w-])")
    for path, lines in corpus.files.items():
        if path == seed:
            continue
        numbers = [number for number, line in enumerate(lines) if mention.search(line)]
        if numbers:
            merge(row(path, MENTION_WEIGHT * len(numbers), numbers[0] + 1, lines[numbers[0]]))
    return ranked(list(scores.values()), limit), []


def render_text(rows: list[dict], notes: list[str]) -> str:
    lines = list(notes)
    for item in rows:
        snippet = item["text"].strip()
        if len(snippet) > SNIPPET_CHARS:
            snippet = snippet[:SNIPPET_CHARS - 3] + "..."
        lines.append(f"{item['path']}:{item['line']}: {snippet}")
    if not rows:
        lines.append("no matches")
    return "\n".join(lines) + "\n"


def render_json(command: str, rows: list[dict], notes: list[str], terms=None) -> str:
    payload = {"schema_version": SCHEMA_VERSION, "command": command,
               "results": [{"path": item["path"], "score": item["score"], "line": item["line"]} for item in rows]}
    if terms is not None:
        payload["terms"] = terms
    if notes:
        payload["notes"] = notes
    return json.dumps(payload, ensure_ascii=False) + "\n"


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="print JSON")
    common.add_argument("--limit", type=int, default=argparse.SUPPRESS, help=f"files to print (default {DEFAULT_LIMIT})")
    common.add_argument("--root", default=argparse.SUPPRESS, help="directory to search (default: current directory)")
    main = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                   parents=[common])
    commands = main.add_subparsers(dest="command", required=True)
    commands.add_parser("find", parents=[common], help="rank files for a plain-language question").add_argument("text")
    commands.add_parser("callers", parents=[common], help="files that use a symbol").add_argument("symbol")
    path = commands.add_parser("path", parents=[common], help="import chain from module A to module B")
    path.add_argument("start")
    path.add_argument("goal")
    commands.add_parser("affected", parents=[common], help="files that depend on a file or file::Symbol").add_argument("target")
    return main


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parser().parse_args(argv)
    limit = getattr(args, "limit", DEFAULT_LIMIT)
    if limit < 1:
        print("--limit must be at least 1", file=sys.stderr)
        return 2
    root = Path(getattr(args, "root", ".")).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    corpus = Corpus(root)
    terms = None
    if args.command == "find":
        rows, terms = find(corpus, args.text, limit)
        notes = [] if terms else ["no search terms left after dropping stop words"]
    elif args.command == "callers":
        rows, notes = callers(corpus, args.symbol, limit), []
    elif args.command == "path":
        rows, notes = module_path(corpus, args.start, args.goal, limit)
    else:
        rows, notes = affected(corpus, args.target, limit)
    output = (render_json(args.command, rows, notes, terms) if getattr(args, "json", False)
              else render_text(rows, notes))
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
