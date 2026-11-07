#!/usr/bin/env python3
"""Regenerable, read-only code index: find, callers, import paths, affected files and a one-page overview.

Python files are parsed with ast, never imported or run; a file this Python
cannot parse gets a regex pass instead. JavaScript and TypeScript files get a
scanner (comments, strings, template text and regular expressions blanked, then
declarations, imports and call sites read with bracket matching) whose calls
resolve through imports (relative paths, index files, tsconfig/jsconfig baseUrl
and paths), this/super, class bases and the types the source writes. Markdown
headings, shell functions and JSON/TOML/YAML keys get a light name pass, and
other text files a word pass.

The index is kept as two JSON files per indexed root in the user's local cache
directory ($XDG_CACHE_HOME/oaw/code-index, ~/.cache/oaw/code-index or
%LOCALAPPDATA%\\oaw\\code-index), or in a directory you name (--cache DIR or
OAW_CODE_INDEX_CACHE); --no-cache builds it in memory and writes nothing. The
cache records each file's size, mtime, inode change time and sha256: a file
whose stat changed is hashed again and re-indexed when its content changed
(with --frozen: reported, not re-indexed). Nothing is written inside the
indexed tree unless you name a cache directory there. Results are pointers to
read (path, line, one source line), ranked by word statistics or resolved by
name: not verified facts, not descriptions of behavior, and not model output.
callers and affected say whether a list is complete within the index.
"""

from __future__ import annotations

import argparse
import ast
import bisect
import builtins
from collections import Counter, deque
from functools import lru_cache
import hashlib
import json
import keyword
import math
import os
import posixpath
import re
import stat
import sys
import tempfile
import time
import warnings

SCHEMA_VERSION = 1  # JSON output contract.
INDEX_VERSION = 2  # Cached record layout; a cache with another value is rebuilt.
MAX_FILE_BYTES = 1024 * 1024
CACHE_ENV = "OAW_CODE_INDEX_CACHE"
SKIP_DIRS = frozenset((".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv", ".tox", ".nox",
                       ".mypy_cache", ".pytest_cache", ".ruff_cache", ".eggs"))
BINARY_SUFFIXES = frozenset(
    "png jpg jpeg gif bmp ico webp svg svgz pdf zip gz tgz bz2 xz 7z tar whl egg jar class so dll dylib exe bin "
    "pyc pyo pyd woff woff2 ttf otf eot mp3 mp4 wav ogg mov avi sqlite db pkl npy npz parquet lock".split())
KINDS = {".py": "python", ".pyw": "python", ".pyi": "python", ".md": "markdown", ".markdown": "markdown",
         ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".ps1": "shell", ".json": "json",
         ".toml": "toml", ".ini": "toml", ".cfg": "toml", ".yml": "yaml", ".yaml": "yaml",
         ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
         ".ts": "javascript", ".tsx": "javascript", ".mts": "javascript", ".cts": "javascript"}
CODE_KINDS = frozenset(("python", "python-regex", "shell", "javascript"))
# sync_examples.py marks a generated example tree with this manifest and an
# installation_id starting with GENERATED_PREFIX; its managed_files are copies.
GENERATED_MARKER = (".oaw", "install.json")
GENERATED_PREFIX = "generated-example-"
STDLIB = frozenset(getattr(sys, "stdlib_module_names", ()))
BUILTINS = frozenset(dir(builtins))
LINK_TAGS = (0xA000000C, 0xA0000003)  # Windows symlink and junction reparse tags; cloud placeholders are files.

# How much one occurrence of a word counts in a unit, by where it occurs.
W_NAME, W_QUAL, W_PARAM, W_DOC, W_COMMENT, W_STRING, W_IDENT, W_TEXT = 4.0, 1.5, 1.0, 2.0, 1.5, 1.0, 0.6, 1.0
W_HEADING, W_KEY, W_PATH_STEM, W_PATH_DIR = 3.0, 2.0, 2.5, 0.8
K1, B = 1.2, 0.5  # BM25 saturation and length normalization.
FILE_WEIGHT = 0.5  # Share of the whole-file score added to the best unit's score.
SYNONYM_WEIGHT = 0.4
TEST_FACTOR, DOC_FACTOR = 0.6, 0.45  # Tests and prose rank lower unless the query asks for them.

STOPWORDS = frozenset("""
a an and are as at be been being but by can could did do does done for from had has have how i if in into is it
its me my no nor not of off on or our ours should so such than that the their them then there these they this
those to too us was we were what when where which while who whom why will with would you your also via per just
only any all each every both either about self cls www com org e g eg ie etc
""".split())
QUESTION_WORDS = frozenset("""
code codes file files function functions method methods class classes implement implements implemented
implementation define defines defined definition locate located location find finds show shows tell module
modules logic responsible happen happens place part piece thing things somewhere something where which
""".split())
DOC_WORDS = frozenset("doc docs documentation documented document readme guide changelog reference manual md wiki "
                      "note notes plan spec described describe describes explained explain".split())
TEST_WORDS = frozenset("test tests tested testing regression regressions fixture fixtures unittest".split())
SYNONYMS = (
    ("delete", "remove", "unlink", "rm"), ("dir", "directory", "folder"), ("config", "configuration", "settings", "cfg"),
    ("check", "validate", "verify", "lint"), ("init", "initialize", "setup", "install"),
    ("arg", "argument", "param", "parameter", "option", "flag"), ("doc", "documentation", "docs"),
    ("repo", "repository"), ("tmp", "temp", "temporary"), ("err", "error", "exception", "failure"),
    ("msg", "message"), ("cmd", "command"), ("db", "database"), ("auth", "authentication", "login"),
    ("secret", "credential", "token", "password"), ("hash", "digest", "sha256", "checksum"),
    ("write", "save", "store", "persist"), ("read", "load"), ("run", "execute", "exec", "invoke", "spawn"),
    ("start", "launch"), ("search", "lookup", "query"), ("url", "link", "href"), ("print", "output", "render"),
    ("copy", "clone", "duplicate"), ("rename", "move"), ("stale", "outdated", "expired"),
    ("symlink", "junction"), ("windows", "nt", "win32"), ("backup", "snapshot"), ("size", "bytes", "length"),
    ("count", "number", "total"), ("time", "timestamp", "date"), ("cli", "command"), ("env", "environment"),
)

DYNAMIC_IMPORTS = frozenset(("importlib.import_module", "import_module", "__import__"))
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]{2,}")
_CAMEL = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
_DRIVE = re.compile(r"^[A-Za-z]:")


class CodeIndexError(Exception):
    """A handled failure: printed as one line, exit status 1."""


# ---------------------------------------------------------------- words


@lru_cache(maxsize=65536)
def _stem(word):
    """A small suffix stripper so that parse/parses/parsed/parsing meet; identical for index and query."""
    if len(word) <= 3 or not word.isascii() or not word.isalpha():
        return word
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    elif word.endswith("sses"):
        word = word[:-2]
    elif word.endswith("s") and not word.endswith(("ss", "us", "is")):
        word = word[:-1]
    stripped = False
    if word.endswith("ing") and len(word) > 5:
        word, stripped = word[:-3], True
    elif word.endswith("ed") and len(word) > 4:
        word, stripped = word[:-2], True
    if stripped and len(word) > 2 and word[-1] == word[-2] and word[-1] not in "lsz":
        word = word[:-1]
    if word.endswith("e") and len(word) > 3:
        word = word[:-1]
    return word


@lru_cache(maxsize=131072)
def _ident_terms(ident):
    """snake_case and camelCase parts, stemmed, plus the joined identifier when it has several parts."""
    parts = [part for chunk in ident.split("_") if chunk for part in _CAMEL.findall(chunk)]
    terms = []
    for part in parts:
        low = part.lower()
        if len(low) > 1 and low not in STOPWORDS:
            terms.append(_stem(low))
    if len(parts) > 1:
        joined = "".join(parts).lower()
        if len(joined) > 3:
            terms.append(joined)
    return tuple(terms)


def words(text):
    """Index terms of free text: identifier parts and CJK character bigrams."""
    terms = []
    for ident in _IDENT.findall(text):
        terms.extend(_ident_terms(ident))
    if not text.isascii():
        for run in _CJK.findall(text):
            terms.extend([run] if len(run) == 1 else [run[i:i + 2] for i in range(len(run) - 1)])
    return terms


def _add_ident(terms, ident, weight):
    for term in _ident_terms(ident):
        terms[term] = terms.get(term, 0.0) + weight


def _add_text(terms, text, weight):
    for term in words(text):
        terms[term] = terms.get(term, 0.0) + weight


_SYNONYM_MAP = {}
for _group in SYNONYMS:
    _stems = [_stem(word) for word in _group]
    for _word in _stems:
        _SYNONYM_MAP.setdefault(_word, set()).update(stem for stem in _stems if stem != _word)
del _group, _stems, _word


def query_bases(text):
    """Split a query into scoring bases: (display word, [(term, weight)], counts toward coverage)."""
    bases, seen = [], set()
    for match in _IDENT.finditer(text):
        ident = match.group()
        parts = [part for chunk in ident.split("_") if chunk for part in _CAMEL.findall(chunk)]
        kept = [part for part in parts if part.lower() not in STOPWORDS
                and (len(parts) > 1 or part.lower() not in QUESTION_WORDS) and len(part) > 1]
        for part in kept:
            term = _stem(part.lower())
            if term in seen:
                continue
            seen.add(term)
            variants = [(term, 1.0)] + [(synonym, SYNONYM_WEIGHT) for synonym in sorted(_SYNONYM_MAP.get(term, ()))]
            bases.append((part.lower(), variants, True))
        if len(parts) > 1:
            joined = "".join(parts).lower()
            if len(joined) > 3 and joined not in seen:
                seen.add(joined)
                bases.append((ident, [(joined, 1.0)], False))
    if not text.isascii():
        for run in _CJK.findall(text):
            for term in [run] if len(run) == 1 else [run[i:i + 2] for i in range(len(run) - 1)]:
                if term not in seen:
                    seen.add(term)
                    bases.append((term, [(term, 1.0)], True))
    return bases


def _path_terms(path):
    """Words of a repository path: the file name counts more than its directories."""
    directory, _, name = path.rpartition("/")
    terms = {}
    _add_text(terms, directory.replace(".", " "), W_PATH_DIR)
    stem = name.rsplit(".", 1)[0] if "." in name.lstrip(".") else name
    _add_ident(terms, stem.replace("-", "_").replace(".", "_"), W_PATH_STEM)
    return terms


def _lines(text):
    """Split like ast counts lines (\\n, \\r\\n, \\r), not like str.splitlines()."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _new_unit(name, kind, line, start, end, doc=""):
    # [name, kind, line, start, end, doc, terms, length(, header end)]: units are searched as small documents.
    return [name, kind, line, start, end, doc, {}, 0.0]


def _first_line(text, limit=120):
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:limit]
    return ""


# ---------------------------------------------------------------- Python


def _chain(node):
    """Dotted text of a call target or attribute: 'a.b.c', 'self.x', 'super().f', or '?.f' for an expression."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "super":
        parts.append("super()")
    elif parts:
        parts.append("?")
    else:
        return None
    return ".".join(reversed(parts))


def _python_comments(lines):
    """(line, text, whole_line, column) for each # comment, skipping '#' in strings and triple-quoted blocks."""
    comments, triple = [], None
    for number, line in enumerate(lines, 1):
        if triple is None and "#" not in line and '"""' not in line and "'''" not in line:
            continue
        if triple is not None and triple not in line:
            continue
        index, size, quote = 0, len(line), None
        while index < size:
            char = line[index]
            if triple is not None:
                end = line.find(triple, index)
                if end < 0:
                    break
                index, triple = end + 3, None
                continue
            if quote is not None:
                if char == "\\":
                    index += 2
                    continue
                if char == quote:
                    quote = None
            elif char == "#":
                comments.append((number, line[index + 1:].strip(), not line[:index].strip(), index))
                break
            elif char in "\"'":
                if line.startswith(char * 3, index):
                    triple = char * 3
                    index += 3
                    continue
                quote = char
            index += 1
    return comments


def _owner_map(units, count):
    """For each line, the index of the innermost unit that contains it (0 is the file-level unit)."""
    owner = [0] * (count + 2)
    for index in sorted(range(1, len(units)), key=lambda i: (units[i][3], -units[i][4])):
        start, end = units[index][3], min(units[index][4], count)
        if end >= start:
            owner[start:end + 1] = [index] * (end - start + 1)
    return owner


def _attach_comments(units, lines, comments):
    owner = _owner_map(units, len(lines))
    starts = {}
    for index, unit in enumerate(units[1:], 1):
        starts.setdefault(unit[3], index)
    for number, text, whole_line, _column in comments:
        index = owner[number] if number < len(owner) else 0
        if whole_line:  # A comment block directly above a definition describes it.
            following = number + 1
            while following <= len(lines) and lines[following - 1].lstrip().startswith("#"):
                following += 1
            index = starts.get(following, index)
        _add_text(units[index][6], text, W_COMMENT)


class _PythonIndexer(ast.NodeVisitor):
    """One pass over a module: units for search, plus definitions, imports, calls and references."""

    def __init__(self, lines):
        self.module = _new_unit("", "module", 1, 1, max(1, len(lines)))
        self.units = [self.module]
        self.defs, self.imports, self.calls, self.refs, self.assigns = [], [], [], [], []
        self.bases, self.syspath, self.docstrings = {}, [], set()
        self.commands = []  # (subcommand, help text) from argparse add_parser calls
        self.strings, self.syspath_names = {}, set()  # module-level string constants; names put on sys.path
        self.stack = [("", "module", self.module)]
        self.main = None  # line of `if __name__ == "__main__":`

    def _docstring(self, node, unit):
        body = getattr(node, "body", None)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            self.docstrings.add(id(body[0].value))
            doc = ast.get_docstring(node) or ""
            unit[5] = _first_line(doc)
            _add_text(unit[6], doc[:8000], W_DOC)
            return getattr(body[0], "end_lineno", None) or body[0].lineno
        return None

    def _definition(self, node, kind):
        parent, parent_kind, _ = self.stack[-1]
        if kind == "function" and parent_kind == "class":
            kind = "method"
        qualname = f"{parent}.{node.name}" if parent else node.name
        end = getattr(node, "end_lineno", None) or node.lineno
        start = min([node.lineno] + [decorator.lineno for decorator in node.decorator_list])
        unit = _new_unit(qualname, kind, node.lineno, start, end)
        self.units.append(unit)
        self.defs.append([qualname, kind, node.lineno, end])
        _add_ident(unit[6], node.name, W_NAME)
        for part in parent.split(".") if parent else ():
            _add_ident(unit[6], part, W_QUAL)
        for decorator in node.decorator_list:
            chain = _chain(decorator.func if isinstance(decorator, ast.Call) else decorator)
            if chain:
                _add_ident(unit[6], chain.rsplit(".", 1)[-1], W_IDENT)
        # Header: decorators, signature and docstring; a match there points at the definition line.
        unit.append(self._docstring(node, unit) or max(node.lineno, node.body[0].lineno - 1))
        return qualname, kind, unit

    def visit_Module(self, node):
        self._docstring(node, self.module)
        for statement in node.body:
            self.visit(statement)

    def visit_FunctionDef(self, node):
        for decorator in node.decorator_list:
            self.visit(decorator)
        qualname, kind, unit = self._definition(node, "function")
        self.stack.append((qualname, kind, unit))
        arguments = node.args
        for argument in (arguments.posonlyargs + arguments.args + arguments.kwonlyargs
                         + [extra for extra in (arguments.vararg, arguments.kwarg) if extra]):
            _add_ident(unit[6], argument.arg, W_PARAM)
            if argument.annotation is not None:
                self.visit(argument.annotation)
        for default in arguments.defaults + [value for value in arguments.kw_defaults if value is not None]:
            self.visit(default)
        if node.returns is not None:
            self.visit(node.returns)
        for statement in node.body:
            self.visit(statement)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        for expression in node.decorator_list + node.bases + [item.value for item in node.keywords]:
            self.visit(expression)
        qualname, kind, unit = self._definition(node, "class")
        self.bases[qualname] = [chain for chain in map(_chain, node.bases) if chain]
        for chain in self.bases[qualname]:
            _add_ident(unit[6], chain.rsplit(".", 1)[-1], W_QUAL)
        self.stack.append((qualname, kind, unit))
        for statement in node.body:
            self.visit(statement)
        self.stack.pop()

    def visit_Assign(self, node):
        self._assignment(node, node.targets, node.value)

    def visit_AnnAssign(self, node):
        self._assignment(node, [node.target], node.value, node.annotation)

    def _assignment(self, node, targets, value, annotation=None):
        scope, kind, _ = self.stack[-1]
        if isinstance(value, ast.Call):
            chain = _chain(value.func)
            first = value.args[0] if value.args else None
            if (chain in DYNAMIC_IMPORTS and isinstance(first, ast.Constant) and isinstance(first.value, str)
                    and len(targets) == 1 and isinstance(targets[0], ast.Name)):
                self.imports.append([node.lineno, scope, first.value, 0, None, targets[0].id])
                chain = None  # An import binding, not an instance of a class.
            for target in targets if chain else ():
                if isinstance(target, ast.Name):
                    self.assigns.append([scope, target.id, chain])
                elif (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                      and target.value.id == "self"):
                    self.assigns.append([scope, "self." + target.attr, chain])
        names = ([name.id for target in targets for name in ast.walk(target) if isinstance(name, ast.Name)]
                 if kind in ("module", "class") else [])
        if kind == "module" and value is not None:
            for name in names:
                self.strings[name] = [item.value for item in ast.walk(value)
                                      if isinstance(item, ast.Constant) and isinstance(item.value, str)][:5]
        if not names:
            self.generic_visit(node)
            return
        end = getattr(node, "end_lineno", None) or node.lineno
        unit = _new_unit(f"{scope}.{names[0]}" if scope else names[0], "variable", node.lineno, node.lineno, end)
        self.units.append(unit)
        for name in names:
            self.defs.append([f"{scope}.{name}" if scope else name, "variable", node.lineno, end])
            _add_ident(unit[6], name, W_NAME)
        for part in scope.split(".") if scope else ():
            _add_ident(unit[6], part, W_QUAL)
        self.stack.append((scope, kind, unit))
        for child in (value, annotation):
            if child is not None:
                self.visit(child)
        for target in targets:
            if not isinstance(target, ast.Name):
                self.visit(target)
        self.stack.pop()

    def visit_If(self, node):
        test = node.test
        if (len(self.stack) == 1 and isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq) and len(test.comparators) == 1):
            sides = [test.left, test.comparators[0]]
            if any(isinstance(side, ast.Name) and side.id == "__name__" for side in sides) and any(
                    isinstance(side, ast.Constant) and side.value == "__main__" for side in sides):
                self.main = self.main or node.lineno
        self.generic_visit(node)

    def visit_Import(self, node):
        scope, _, unit = self.stack[-1]
        for alias in node.names:
            self.imports.append([node.lineno, scope, alias.name, 0, None, alias.asname])
            for part in alias.name.split(".") + ([alias.asname] if alias.asname else []):
                _add_ident(unit[6], part, W_IDENT)

    def visit_ImportFrom(self, node):
        scope, _, unit = self.stack[-1]
        for alias in node.names:
            self.imports.append([node.lineno, scope, node.module or "", node.level or 0, alias.name, alias.asname])
            for part in (node.module or "").split(".") + [alias.name] + ([alias.asname] if alias.asname else []):
                if part and part != "*":
                    _add_ident(unit[6], part, W_IDENT)

    def visit_Call(self, node):
        scope, _, unit = self.stack[-1]
        func = node.func
        chain = _chain(func)
        if chain:
            self.calls.append([node.lineno, scope, chain])
            _add_ident(unit[6], chain.rsplit(".", 1)[-1], W_IDENT)
            if chain in ("sys.path.insert", "sys.path.append"):
                for item in (item for argument in node.args for item in ast.walk(argument)):
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        self.syspath.append(item.value)
                    elif isinstance(item, ast.Name):
                        self.syspath_names.add(item.id)
            elif chain.endswith("add_parser") and node.args and isinstance(node.args[0], ast.Constant):
                texts = [item.value.value for item in node.keywords if item.arg in ("help", "description")
                         and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str)]
                if isinstance(node.args[0].value, str) and texts:
                    self.commands.append((node.args[0].value, " ".join(texts), unit))
            base = func.value if isinstance(func, ast.Attribute) else None
            while isinstance(base, ast.Attribute):
                _add_ident(unit[6], base.attr, W_IDENT)
                base = base.value
            if base is not None:
                self.visit(base)
        else:
            self.visit(func)
        for argument in node.args:
            self.visit(argument)
        for item in node.keywords:
            if item.arg:
                _add_ident(unit[6], item.arg, W_IDENT)
            self.visit(item.value)

    def visit_Attribute(self, node):
        scope, _, unit = self.stack[-1]
        chain = _chain(node)
        if chain and isinstance(node.ctx, ast.Load) and not chain.startswith(("?", "self.", "cls.", "super()")):
            self.refs.append([node.lineno, scope, chain])
        base = node
        while isinstance(base, ast.Attribute):
            _add_ident(unit[6], base.attr, W_IDENT)
            base = base.value
        self.visit(base)

    def visit_Name(self, node):
        _add_ident(self.stack[-1][2][6], node.id, W_IDENT)

    def visit_Constant(self, node):
        if isinstance(node.value, str) and id(node) not in self.docstrings:
            _add_text(self.stack[-1][2][6], node.value[:4000], W_STRING)


def _attach_commands(units, commands):
    """An argparse subcommand's help text describes the function of the same name in this file: move it there."""
    by_name = {}
    for unit in units:
        if unit[1] in ("function", "method"):
            by_name.setdefault(unit[0].rsplit(".", 1)[-1], unit)
    for command, text, owner in commands:
        name = re.sub(r"\W", "_", command)
        for candidate in (name, "cmd_" + name, "_cmd_" + name, "do_" + name, "command_" + name, "_" + name):
            if candidate in by_name:
                _add_text(by_name[candidate][6], text, W_DOC)
                for term in words(text):
                    left = owner[6].get(term, 0.0) - W_STRING
                    if left > 0.01:
                        owner[6][term] = left
                    else:
                        owner[6].pop(term, None)
                break


def _bound_names(imports):
    names = set()
    for _line, _scope, module, _level, name, alias in imports:
        names.add(alias or (module.split(".")[0] if name is None else name))
    return names


def _python_record(lines, text):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tree = ast.parse(text)
    indexer = _PythonIndexer(lines)
    indexer.visit(tree)
    _attach_comments(indexer.units, lines, _python_comments(lines))
    _attach_commands(indexer.units, indexer.commands)
    for name in sorted(indexer.syspath_names):  # sys.path.insert(0, str(SCRIPTS)) with SCRIPTS = ... / "scripts"
        indexer.syspath.extend(indexer.strings.get(name, ()))
    bound = _bound_names(indexer.imports)
    refs = [ref for ref in indexer.refs if ref[2].split(".", 1)[0] in bound]
    python = {"defs": indexer.defs, "imports": indexer.imports, "calls": indexer.calls, "refs": refs,
              "assigns": indexer.assigns, "bases": indexer.bases, "syspath": indexer.syspath[:20]}
    if indexer.main:
        python["main"] = indexer.main
    return indexer.units, python


_PY_DEF = re.compile(r"^(\s*)(?:async\s+def|def|class)\s+([A-Za-z_]\w*)(.*)")
_PY_IMPORT = re.compile(r"^\s*import\s+([\w.]+(?:\s+as\s+\w+)?(?:\s*,\s*[\w.]+(?:\s+as\s+\w+)?)*)\s*(?:#.*)?$")
_PY_FROM = re.compile(r"^\s*from\s+(\.*)([\w.]*)\s+import\s+\(?\s*([\w\s,*]+?)\s*\)?\s*(?:#.*)?$")
_PY_CALL = re.compile(r"(?<![\w.])((?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*)\s*\(")
_PY_ASSIGN = re.compile(r"^([A-Za-z_]\w*)\s*(?::[^=\n]*)?=(?!=)")


def _python_fallback(lines):
    """Indentation-scoped regex pass for a file this Python cannot parse (newer syntax, Python 2, errors)."""
    module = _new_unit("", "module", 1, 1, max(1, len(lines)))
    units, defs, imports, calls = [module], [], [], []
    comments = {number: (text, column) for number, text, _, column in _python_comments(lines)}
    stack, last = [], 0  # stack: (indent, qualname, kind, unit)
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        if not stripped.startswith("#"):
            while stack and indent <= stack[-1][0]:
                stack.pop()[3][4] = last
            last = number
        definition = _PY_DEF.match(line)
        if definition:
            parent = stack[-1] if stack else (None, "", "module", module)
            keyword_text = stripped.split(None, 1)[0]
            kind = "class" if keyword_text == "class" else ("method" if parent[2] == "class" else "function")
            name = definition.group(2)
            qualname = f"{parent[1]}.{name}" if parent[1] else name
            unit = _new_unit(qualname, kind, number, number, len(lines))
            units.append(unit)
            defs.append([qualname, kind, number, number])
            _add_ident(unit[6], name, W_NAME)
            _add_text(unit[6], definition.group(3), W_PARAM)
            stack.append((len(definition.group(1)), qualname, kind, unit))
            continue
        scope, unit = (stack[-1][1], stack[-1][3]) if stack else ("", module)
        code = line
        if number in comments:
            _add_text(unit[6], comments[number][0], W_COMMENT)
            code = line[:comments[number][1]]
        if not stack:
            assignment = _PY_ASSIGN.match(line)
            if assignment:
                variable = _new_unit(assignment.group(1), "variable", number, number, number)
                units.append(variable)
                defs.append([assignment.group(1), "variable", number, number])
                _add_ident(variable[6], assignment.group(1), W_NAME)
                _add_text(variable[6], line[assignment.end():], W_IDENT)
                continue
        plain = _PY_IMPORT.match(code)
        if plain:
            for item in plain.group(1).split(","):
                name, _, alias = item.strip().partition(" as ")
                imports.append([number, scope, name.strip(), 0, None, alias.strip() or None])
        relative = _PY_FROM.match(code)
        if relative:
            for item in relative.group(3).split(","):
                name, _, alias = item.strip().partition(" as ")
                if name.strip():
                    imports.append([number, scope, relative.group(2), len(relative.group(1)), name.strip(),
                                    alias.strip() or None])
        for match in _PY_CALL.finditer(code):
            if match.group(1).split(".", 1)[0] not in keyword.kwlist:
                calls.append([number, scope, match.group(1)])
        _add_text(unit[6], code, W_IDENT)
    for entry in stack:
        entry[3][4] = last or len(lines)
    for definition in defs:
        for unit in units:
            if unit[0] == definition[0] and unit[2] == definition[2]:
                definition[3] = unit[4]
    python = {"defs": defs, "imports": imports, "calls": calls, "refs": [], "assigns": [], "bases": {}, "syspath": []}
    main = next((number for number, line in enumerate(lines, 1)
                 if re.match(r"if\s+__name__\s*==\s*['\"]__main__['\"]\s*:", line)), None)
    if main:
        python["main"] = main
    return units, python


# ---------------------------------------------------------------- other text files


_MD_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_SH_FUNC = re.compile(r"^\s*(?:function\s+([A-Za-z_][\w:.-]*)|([A-Za-z_][\w:.-]*)\s*\(\s*\)\s*\{?)")
_SH_COMMENT = re.compile(r"(?:^|\s)#(.*)$")
_TOML_HEADER = re.compile(r"^\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*(?:#.*)?$")
_TOML_KEY = re.compile(r"^\s*([A-Za-z0-9_.\-\"']+)\s*[=:]")
_TOML_COMMENT = re.compile(r"(?:^|\s)[#;](.*)$")
_YAML_HEADER = re.compile(r"^([A-Za-z0-9_.\-\"']+)\s*:")
_YAML_KEY = re.compile(r"^\s+-?\s*([A-Za-z0-9_.\-\"']+)\s*:")
_JSON_KEY = re.compile(r'"((?:[^"\\]|\\.)*)"\s*:')
_JS_DEF = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s*\*?\s*([A-Za-z_$][\w$]*)"
    r"|class\s+([A-Za-z_$][\w$]*)"
    r"|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?(?:function\b|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>))")
_JS_COMMENT = re.compile(r"(?:^|\s)//(.*)$")
TEXT_CHUNK = 50
MAX_SECTIONS = 300


def _markdown_units(lines):
    units = [_new_unit("", "document", 1, 1, len(lines))]
    trail, fence = [], None
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if fence:
            if stripped.startswith(fence):
                fence = None
            else:
                _add_text(units[-1][6], line, W_TEXT)
            continue
        if stripped.startswith(("```", "~~~")):
            fence = stripped[:3]
            continue
        heading = _MD_HEADING.match(line)
        if heading and heading.group(2):
            level = len(heading.group(1))
            title = _MD_LINK.sub(r"\1", heading.group(2)).replace("`", "").strip(" *_")
            units[-1][4] = number - 1
            while trail and trail[-1][0] >= level:
                trail.pop()
            unit = _new_unit(title[:80], "heading", number, number, len(lines))
            _add_text(unit[6], title, W_HEADING)
            for _, parent in trail:
                _add_text(unit[6], parent, W_QUAL)
            trail.append((level, title))
            units.append(unit)
            continue
        _add_text(units[-1][6], line, W_TEXT)
    return units


def _section_units(lines, header, kind, comment=None, key=None, body=W_TEXT):
    """Flat sections split at header lines; each section is one unit named by its header."""
    units = [_new_unit("", "document", 1, 1, len(lines))]
    for number, line in enumerate(lines, 1):
        name = header(line)
        terms = units[-1][6]
        if name:
            units[-1][4] = number - 1
            unit = _new_unit(name.strip("\"'")[:80], kind, number, number, len(lines))
            units.append(unit)
            terms = unit[6]
            _add_text(terms, name, W_HEADING)
        text = line
        found = comment.search(line) if comment else None
        if found:
            _add_text(terms, found.group(1), W_COMMENT)
            text = line[:found.start()]
        if key:
            for name in key(text):
                _add_text(terms, name, W_KEY)
        _add_text(terms, text, body)
    return units


def _text_units(lines, kind="text"):
    units = []
    for start in range(1, len(lines) + 1, TEXT_CHUNK):
        unit = _new_unit("", kind, start, start, min(len(lines), start + TEXT_CHUNK - 1))
        for line in lines[start - 1:start - 1 + TEXT_CHUNK]:
            _add_text(unit[6], line, W_TEXT)
        units.append(unit)
    return units


def _json_units(lines):
    indents = [len(line) - len(line.lstrip()) for line in lines if line.lstrip().startswith('"') and _JSON_KEY.match(
        line.lstrip())]
    if not indents:
        return _text_units(lines, "document")
    top = min(indents)

    def header(line):
        stripped = line.lstrip()
        match = _JSON_KEY.match(stripped) if len(line) - len(stripped) == top else None
        return match.group(1) if match else None

    if sum(1 for line in lines if header(line)) > MAX_SECTIONS:
        units = _text_units(lines, "document")
        for unit in units:
            for line in lines[unit[3] - 1:unit[4]]:
                for name in _JSON_KEY.findall(line):
                    _add_text(unit[6], name, W_KEY)
        return units
    return _section_units(lines, header, "key", key=_JSON_KEY.findall, body=0.8)


def _other_units(kind, lines):
    if kind == "markdown":
        return _markdown_units(lines)
    if kind == "shell":
        def header(line):
            match = _SH_FUNC.match(line)
            return (match.group(1) or match.group(2)) if match else None
        return _section_units(lines, header, "function", comment=_SH_COMMENT)
    if kind == "json":
        return _json_units(lines)
    if kind == "toml":
        def header(line):
            match = _TOML_HEADER.match(line)
            return match.group(1) if match else None
        return _section_units(lines, header, "section", _TOML_COMMENT, lambda text: _TOML_KEY.findall(text), 0.8)
    if kind == "yaml":
        def header(line):
            match = _YAML_HEADER.match(line)
            return match.group(1) if match else None
        return _section_units(lines, header, "key", _SH_COMMENT, lambda text: _YAML_KEY.findall(text), 0.8)
    if kind == "javascript":
        def header(line):
            match = _JS_DEF.match(line)
            return next((group for group in match.groups() if group), None) if match else None
        return _section_units(lines, header, "function", _JS_COMMENT, body=0.8)
    return _text_units(lines)


# ---------------------------------------------------------------- JavaScript and TypeScript
#
# A scanner, not a parser. Comments, strings, template text and regular expression literals are
# blanked first (line breaks kept); declarations, imports and call sites are then read from what is
# left with regular expressions and bracket matching. Calls resolve like Python's: through imports
# (relative paths, index files, tsconfig/jsconfig baseUrl and paths), `this`/`super`, class bases,
# and types written in the source (`x: Foo`, `new Foo()`, parameter and field annotations).
# Not resolved: dynamic dispatch beyond these, inferred types, dependency injection, decorators'
# effects, `any`, computed member names, JSX elements, object-literal methods, and values passed
# around (callbacks, re-assigned variables). Dynamic import() is kept as an import edge only.

JS_SOURCE = (".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs")
_JS_SOURCE_FOR_JS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".d.ts")
_JS_ALTERNATES = {".js": (".ts", ".tsx", ".d.ts"), ".jsx": (".tsx", ".d.ts"), ".mjs": (".mts", ".d.mts"),
                  ".cjs": (".cts", ".d.cts")}
_JS_TOP = re.compile(r"""[^'"`/\\]+|//[^\n]*|/\*.*?(?:\*/|\Z)|'(?:[^'\\\n]|\\.)*'?|"(?:[^"\\\n]|\\.)*"?|.""", re.S)
_JS_INNER = re.compile(r"""[^'"`/\\{}]+|//[^\n]*|/\*.*?(?:\*/|\Z)|'(?:[^'\\\n]|\\.)*'?|"(?:[^"\\\n]|\\.)*"?|.""", re.S)
_JS_TEMPLATE = re.compile(r"(?:[^`\\$]|\\.|\$(?!\{))*", re.S)
_JS_REGEX = re.compile(r"/(?![*/])(?:[^\\/\[\n]|\\.|\[(?:[^\]\\\n]|\\.)*\])+/[A-Za-z]*")
_JS_LAST_WORD = re.compile(r"[\w$]+$")
_JS_BEFORE_REGEX = frozenset("return typeof instanceof in of new delete void throw case do else yield await".split())
_JS_DECL = re.compile(
    r"[ \t]*(?:@[\w$.]+(?:\([^()\n]*\))?[ \t]+)*"
    r"(?P<mods>(?:(?:export|default|declare|abstract|async|public|private|protected|static|readonly|override|accessor)"
    r"[ \t]+)*)"
    r"(?:(?P<kw>function|class)\b[ \t]*\*?[ \t]*(?P<kname>[A-Za-z_$][\w$]*)?"
    r"|(?P<kw2>const[ \t]+enum|interface|enum|type|namespace|module|const|let|var)[ \t]+"
    r"(?P<name2>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)"
    r"|(?P<cjs>(?:module\.)?exports\.)(?P<cname>[A-Za-z_$][\w$]*)[ \t]*=(?!=)"
    r"|(?P<owner>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\.prototype\.(?P<pname>[A-Za-z_$][\w$]*)[ \t]*=(?!=)"
    r"|(?P<lhs>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+)[ \t]*=[ \t]*class\b[ \t]*(?P<xname>[A-Za-z_$][\w$]*)?"
    r"|(?:(?P<acc>get|set)[ \t]+)?\*?[ \t]*(?P<mname>#?[A-Za-z_$][\w$]*)[ \t]*[?!]?[ \t]*(?P<after>[(<:=;]))")
_JS_CALL_REV = re.compile(  # read backwards from a "(": optional ?. and type arguments, a dotted chain, what precedes
    r"\s*(?:\.\?)?\s*(?:>(?:[^<>()\n;{}=&|]|>[^<>()\n;{}=&|]*<)*<\s*)?!?\s*"
    r"(?P<chain>[\w$]+#?(?:\s*\.\??!?\s*[\w$]+#?)*)"
    r"(?P<lead>\s*(?:\.\??!?|wen\b|noitcnuf\b|teg\b|tes\b|cnysa\b|citats\b)?)")
_JS_BRACKET = re.compile(r"[{}()\[\]]")
_JS_CLOSERS = {"}": "{", ")": "(", "]": "["}
_JS_SCAN = re.compile(r"[{;(\[\n]|=>")
_JS_STATEMENT = re.compile(r"[;(\[{)\]}\n]")
_JS_VALUE = re.compile(
    r"\s*(?:async\s+)?(?:(?P<fn>function\b\s*\*?\s*[\w$]*\s*)|(?P<new>new\s+)(?P<cls>[A-Za-z_$][\w$]*(?:\s*\.\s*[A-Za-z_$][\w$]*)*)"
    r"|(?P<cexp>class\b)\s*(?P<xname>[A-Za-z_$][\w$]*)?|(?P<single>[A-Za-z_$][\w$]*)\s*=>|(?P<paren>[(<])"
    r"|(?P<call>(?:this\.)?[A-Za-z_$][\w$]*(?:\s*\.\s*[A-Za-z_$][\w$]*)*)\s*(?P<open>\())")
_JS_ARROW = re.compile(r"\s*(?::[^;{}=]*(?:=>[^;{}=]*)?)?=>\s*")
_JS_PARAM = re.compile(r"(?P<mods>(?:(?:public|private|protected|readonly|override)\s+)*)(?:\.\.\.)?"
                       r"(?P<name>[A-Za-z_$][\w$]*)\s*\??\s*(?::(?P<type>.*))?$", re.S)
_JS_PARAM_DECORATOR = re.compile(r"@[\w$.]+\s*(?:\((?:[^()]|\([^()]*\))*\))?")
_JS_TYPE_NAME = re.compile(r"(?:readonly\s+)?([A-Za-z_$][\w$]*(?:\s*\.\s*[A-Za-z_$][\w$]*)*)\s*(?:<.*>)?$", re.S)
_JS_MODIFIERS_ONLY = re.compile(r"[ \t]*(?:(?:public|private|protected|static|readonly|abstract|async|declare|override)"
                                r"[ \t]+)*")
_JS_THIS_NEW = re.compile(r"this\.(#?[A-Za-z_$][\w$]*)\s*=\s*new\s+([A-Za-z_$][\w$]*(?:\s*\.\s*[A-Za-z_$][\w$]*)*)")
# Matched only where the keyword occurs (a literal search), never by scanning every position.
_JS_IMPORT = re.compile(r"import\s+(?:type\s+)?(?P<clause>[\w$*{}\s,]*?)\s*\bfrom\s*(?P<q>\")")
_JS_IMPORT_SIDE = re.compile(r"import\s*(?P<q>\")")
_JS_IMPORT_EQUALS = re.compile(r"import\s+(?P<local>[A-Za-z_$][\w$]*)\s*=\s*require\s*\(\s*(?P<q>\")")
_JS_DYNAMIC = re.compile(r"import\s*\(\s*(?P<q>\")")
_JS_REEXPORT = re.compile(
    r"export\s+(?:type\s+)?(?P<clause>\*(?:\s+as\s+[A-Za-z_$][\w$]*)?|\{[^{}]*\})\s*from\s*(?P<q>\")")
_JS_EXPORT_LIST = re.compile(r"export\s+(?:type\s+)?\{(?P<list>[^{}]*)\}(?!\s*from\b)")
_JS_EXPORT_DEFAULT = re.compile(r"export\s+default\s+(?!(?:class|function|async|abstract|interface|enum)\b)"
                                r"(?P<name>[A-Za-z_$][\w$]*)\s*(?:;|$)", re.M)
_JS_EXPORT_ASSIGN = re.compile(r"(?:export\s*=|module\.exports\s*=)\s*(?:(?P<name>[A-Za-z_$][\w$]*)\s*(?:;|$)"
                               r"|(?P<obj>\{))", re.M)
_JS_REQUIRE = re.compile(r"require\s*\(\s*(?P<q>\")")
_JS_BINDS_MODULE = re.compile(r"\s*(?:await\s+)?(?:require|import)\s*\(")  # const x = require(...): a binding
_JS_REQUIRE_BIND = re.compile(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*|\{[^{}]*\})\s*=\s*$")
_JS_SPECIFIER = re.compile(r"(?:type\s+)?([\w$]+)(?:\s+as\s+([\w$]+))?")
_JS_KEYWORDS = frozenset("""if for while switch catch function return typeof instanceof in of new delete void throw
case do else yield await async super import export class extends const let var with debugger default try finally
""".split())
_JS_PRIMITIVES = frozenset("""any unknown never void undefined null object this Object Record Partial Readonly
Required Pick Omit Iterable IterableIterator AsyncIterable Thenable""".split())  # say nothing about the class
# Built-in types: a receiver written with one of these is not user code (its methods resolve as external).
_JS_BUILTIN_TYPES = frozenset("""string number boolean symbol bigint Function Array ReadonlyArray Promise Map Set
WeakMap WeakSet ReadonlyMap ReadonlySet Error RegExp Date String Number Boolean Uint8Array ArrayBuffer""".split())
# Language words that Python's ast pass never sees as identifiers: left out of JS/TS search terms.
_JS_NOISE = frozenset("""break case catch class const continue debugger default delete do else enum export extends
false finally for function if import in instanceof new null return super switch this throw true try typeof var void
while with yield let static implements interface private protected public await async of as from type readonly
declare abstract override keyof infer unknown any never undefined string number boolean object symbol bigint""".split())
JS_GLOBALS = frozenset("""console Math JSON Object Array Promise Number String Boolean Symbol Date RegExp Error
TypeError RangeError Map Set WeakMap WeakSet Reflect Proxy parseInt parseFloat isNaN isFinite setTimeout
clearTimeout setInterval clearInterval setImmediate require process Buffer globalThis window document navigator
URL URLSearchParams encodeURIComponent decodeURIComponent encodeURI decodeURI fetch structuredClone
queueMicrotask atob btoa BigInt Uint8Array Int32Array Float64Array ArrayBuffer TextEncoder TextDecoder""".split())


def _js_regex_here(out):
    """Whether a '/' after the code emitted so far starts a regular expression literal (not a division)."""
    for piece in reversed(out):
        stripped = piece.rstrip()
        if stripped:
            last = stripped[-1]
            if last.isalnum() or last in "_$":
                return _JS_LAST_WORD.search(stripped).group() in _JS_BEFORE_REGEX
            if last == ")":
                return _js_control_paren(out)
            return last not in ']"'
    return True


_JS_CONTROL = re.compile(r"(?<![\w$.])(?:if|while|for|with)\s*$")


def _js_control_paren(out, budget=4000):
    """Whether the last ')' emitted closes the condition of if/while/for/with (then a '/' after it starts a
    regular expression; after any other ')' it is a division)."""
    depth = 0
    for number in range(len(out) - 1, -1, -1):
        piece = out[number]
        for index in range(len(piece) - 1, -1, -1):
            budget -= 1
            if budget < 0:
                return False
            char = piece[index]
            if char == ")":
                depth += 1
            elif char == "(":
                depth -= 1
                if depth == 0:
                    before = piece[:index]
                    while len(before.strip()) < 6 and number > 0:  # the keyword may sit in an earlier piece
                        number -= 1
                        before = out[number] + before
                    return bool(_JS_CONTROL.search(before[-40:]))
    return False


def _js_mask(text):
    """(code, strings, comments): comments, strings, template text and regular expressions blanked with
    line breaks kept, strings as '""' keyed by their offset in code -> (offset in text, contents)."""
    out, strings, comments = [], {}, []
    stack, pos, size, length, template = [], 0, len(text), 0, False
    if text.startswith("#!"):
        pos = text.find("\n")
        pos = size if pos < 0 else pos
    while pos < size:
        if template:
            match = _JS_TEMPLATE.match(text, pos)
            breaks = match.group().count("\n")
            if breaks:
                out.append("\n" * breaks)
                length += breaks
            pos, template = match.end(), False
            if pos >= size:
                break
            if text[pos] == "`":
                out.append('"')
                length, pos = length + 1, pos + 1
            else:  # ${ opens an expression: kept as code, in parentheses
                out.append(" (")
                length, pos = length + 2, pos + 2
                stack.append(0)
            continue
        match = (_JS_INNER if stack else _JS_TOP).match(text, pos)
        piece, end = match.group(), match.end()
        first = piece[0]
        if first == "/":
            if piece.startswith("//"):
                comments.append((pos, piece))
                piece = ""
            elif piece.startswith("/*"):
                comments.append((pos, piece))
                piece = "\n" * piece.count("\n") or " "
            elif _js_regex_here(out):
                literal = _JS_REGEX.match(text, pos)
                if literal:
                    piece, end = '""', literal.end()
        elif first in "'\"":
            closed = len(piece) > 1 and piece[-1] == first
            strings[length] = (pos, piece[1:-1] if closed else piece[1:])
            piece = '""' + "\n" * piece.count("\n")
        elif first == "`":
            out.append('"')
            length, pos, template = length + 1, end, True
            continue
        elif stack and first == "{":
            stack[-1] += 1
        elif stack and first == "}":
            if stack[-1] == 0:
                stack.pop()
                out.append(") ")
                length, pos, template = length + 2, end, True
                continue
            stack[-1] -= 1
        out.append(piece)
        length += len(piece)
        pos = end
    return "".join(out), strings, comments


def _js_brackets(code, points):
    """Matching bracket offsets, and for each point (sorted offsets) the innermost open bracket around it."""
    pairs, stack, around, index, count = {}, [], [], 0, len(points)
    for match in _JS_BRACKET.finditer(code):
        at = match.start()
        while index < count and points[index] < at:
            around.append(stack[-1][1] if stack else -1)
            index += 1
        char = match.group()
        if char in "{([":
            stack.append((char, at))
            continue
        want = _JS_CLOSERS[char]
        for depth in range(len(stack) - 1, max(-1, len(stack) - 4), -1):
            if stack[depth][0] == want:
                pairs[stack[depth][1]] = at
                del stack[depth:]
                break
    while index < count:
        around.append(stack[-1][1] if stack else -1)
        index += 1
    return pairs, around


def _js_split(text, separator=","):
    """Split at separator characters outside brackets (and outside <...> type arguments)."""
    parts, depth, start, index, size = [], 0, 0, 0, len(text)
    while index < size:
        char = text[index]
        if char == "=" and text.startswith("=>", index):
            index += 2
            continue
        if char in "([{<":
            depth += 1
        elif char in ")]}>":
            depth = max(0, depth - 1)
        elif char == separator and depth == 0:
            parts.append(text[start:index])
            start = index + 1
        index += 1
    parts.append(text[start:])
    return parts


def _js_type(text):
    """The class or interface name a type annotation names ('Foo', 'ns.Foo'), or None."""
    if not text:
        return None
    kept = [part.strip() for part in _js_split(text.strip(), "|")]
    kept = [part for part in kept if part and part not in ("undefined", "null", "void")]
    if len(kept) != 1:
        return None
    if kept[0].endswith("[]"):
        return "!Array"
    match = _JS_TYPE_NAME.match(kept[0])
    if not match:
        return None
    chain = re.sub(r"\s+", "", match.group(1))
    if chain in _JS_BUILTIN_TYPES:
        return "!" + chain
    return None if chain in _JS_PRIMITIVES else chain


def _js_params(text):
    """(name, type, is_property) for each parameter in a parameter list's text; a destructuring pattern
    ({a, b: c}, [d, ...e], with defaults) gives each name it binds, type unknown."""
    found = []
    for piece in _js_split(text):
        piece = _JS_PARAM_DECORATOR.sub(" ", piece).strip()
        default = _js_split(piece, "=")
        head = default[0].strip() if default else ""
        if head.startswith("..."):
            head = head[3:].lstrip()
        if head[:1] in ("{", "["):
            found.extend((name, None, False) for name in _js_pattern_names(head))
            continue
        match = _JS_PARAM.match(head) if head else None
        if match:
            found.append((match.group("name"), _js_type(match.group("type")), bool(match.group("mods"))))
    return found


def _js_pattern_names(text, depth=0):
    """Names a destructuring pattern starting at text[0] ('{' or '[') binds."""
    level, close = 0, None
    for index, char in enumerate(text):
        if char in "{[(":
            level += 1
        elif char in "}])":
            level -= 1
            if level == 0:
                close = index
                break
    if close is None or depth > 8:
        return []
    names, is_object = [], text[0] == "{"
    for element in _js_split(text[1:close]):
        element = element.strip()
        if element.startswith("..."):
            element = element[3:].lstrip()
        if is_object:
            parts = _js_split(element, ":")
            element = ":".join(parts[1:]).strip() if len(parts) > 1 else element
        element = _js_split(element, "=")[0].strip() if element else ""
        if element[:1] in ("{", "["):
            names.extend(_js_pattern_names(element, depth + 1))
        elif re.fullmatch(r"[A-Za-z_$][\w$]*", element):
            names.append(element)
    return names


def _js_skip(code, pos):
    """Position after whitespace."""
    size = len(code)
    while pos < size and code[pos] in " \t\n":
        pos += 1
    return pos


def _js_generics(code, pos):
    """Position after a <...> type parameter list starting at pos (pos itself when there is none)."""
    if pos >= len(code) or code[pos] != "<":
        return pos
    depth, index, stop = 0, pos, min(len(code), pos + 1000)
    while index < stop:
        char = code[index]
        if char == "=" and code.startswith("=>", index):
            index += 2
            continue
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
            if depth == 0:
                return index + 1
        elif char in ";{":
            return pos
        index += 1
    return pos


def _js_body(code, pos, pairs, header=False):
    """Offset of the '{' that opens a body after a parameter list (or a class header) ending at pos."""
    stop = min(len(code), pos + (4000 if header else 1500))
    while pos < stop:
        match = _JS_SCAN.search(code, pos, stop)
        if not match:
            return None
        token, at = match.group(), match.start()
        if token == ";":
            return None
        if token in "([":
            close = pairs.get(at)
            if close is None:
                return None
            pos = close + 1
            continue
        if token == "=>":
            pos = at + 2
            continue
        before = code[max(0, at - 200):at].rstrip()
        if token == "\n":
            if header:
                pos = at + 1
                continue
            after = _js_skip(code, at)
            if after < len(code) and (code[after] in "{:|&.>=" or (before and before[-1] in ":|&,<(=")):
                pos = at + 1
                continue
            return None
        if before and before[-1] in ":|&<," and not header:  # an object type in a return annotation
            close = pairs.get(at)
            if close is None:
                return None
            pos = close + 1
            continue
        return at
    return None


def _js_end(code, pos, pairs):
    """Offset where the expression or statement starting at pos ends (an arrow body, a type alias)."""
    pos = _js_skip(code, pos)
    size = len(code)
    stop = min(size, pos + 20000)
    while pos < stop:
        match = _JS_STATEMENT.search(code, pos, stop)
        if not match:
            return stop
        token, at = match.group(), match.start()
        if token in "([{":
            close = pairs.get(at)
            if close is None:
                return at
            pos = close + 1
            continue
        if token != "\n":
            return at
        before = code[max(0, at - 200):at].rstrip()
        after = _js_skip(code, at)
        if (before and before[-1] in "=+-*/%&|^!?:,.<>(") or (after < size and code[after] in ".?:+-*/%&|^=><"):
            pos = at + 1
            continue
        return at
    return stop


def _js_value(code, pos, pairs):
    """What an initializer at pos is: ('function', params open, body open or None, end), ('new', type),
    ('class', name or None, header end) or None."""
    match = _JS_VALUE.match(code, pos)
    if not match:
        return None
    if match.group("call"):  # `= factory(...)` alone: its written return type types the variable
        if match.group("call") in ("require", "import"):  # module bindings, kept with the imports
            return None
        close = pairs.get(match.start("open"))
        after = _js_skip(code, close + 1) if close is not None else len(code)
        if close is None or (after < len(code) and code[after] not in ";,)}" and code[close + 1:after].count("\n") == 0):
            return None
        return ("call", re.sub(r"\s+", "", match.group("call")) + "()")
    if match.group("new"):
        return ("new", re.sub(r"\s+", "", match.group("cls")))
    if match.group("cexp"):
        return ("class", match.group("xname"), match.end())
    if match.group("single"):  # x => ...: the fifth item names the one parameter
        end_arrow = match.end()
        body = _js_skip(code, end_arrow)
        if body < len(code) and code[body] == "{" and body in pairs:
            return ("function", None, body, pairs[body], match.group("single"))
        return ("function", None, None, _js_end(code, end_arrow, pairs), match.group("single"))
    if match.group("fn") is not None:
        opening = _js_skip(code, _js_generics(code, match.end()))
        close = pairs.get(opening) if opening < len(code) and code[opening] == "(" else None
        if close is None:
            return None
        body = _js_body(code, close + 1, pairs)
        return ("function", opening, body, pairs.get(body, close) if body is not None else close)
    opening = _js_skip(code, _js_generics(code, match.start("paren")))
    if opening >= len(code) or code[opening] != "(" or opening not in pairs:
        return None
    close = pairs[opening]
    arrow = _JS_ARROW.match(code, close + 1)
    if not arrow:
        return None
    body = arrow.end()
    if body < len(code) and code[body] == "{" and body in pairs:
        return ("function", opening, body, pairs[body])
    return ("function", opening, None, _js_end(code, body, pairs))


def _js_returns(code, close, body):
    """The class or interface a function's written return type names (text between ')' and its body)."""
    text = code[close + 1:body if body is not None else min(len(code), close + 300)].strip()
    if not text.startswith(":"):
        return None
    text = text[1:]
    for stop in (";", "\n", "{"):
        if body is None and stop in text:
            text = text[:text.index(stop)]
    return _js_type(text.rstrip(" ={"))


def _js_type_and_value(code, pos, pairs):
    """(annotation text, offset after '=') of a declaration's ': Type = value' part starting at pos."""
    index = _js_skip(code, pos)
    if index < len(code) and code[index] == "!":
        index = _js_skip(code, index + 1)
    if index < len(code) and code[index] == "=" and not code.startswith("=>", index):
        return None, index + 1
    if index >= len(code) or code[index] != ":":
        return None, None
    start = index + 1
    stop = min(len(code), start + 2000)
    index = start
    while index < stop:
        char = code[index]
        if char in "([{":
            close = pairs.get(index)
            if close is None:
                return code[start:index], None
            index = close + 1
            continue
        if char == "=":
            if code.startswith("=>", index):
                index += 2
                continue
            return code[start:index], index + 1
        if char in ";,)\n}":
            return code[start:index], None
        index += 1
    return code[start:index], None


def _plain_scope(scope):
    """A scope without the "{line}" parts that name let/const blocks: what to show for it."""
    return ".".join(part for part in scope.split(".") if not (part.startswith("{") and part.endswith("}"))) \
        if "{" in scope else scope


def _owner_scope(scope):
    """The definition a scope belongs to: trailing "{line}" block parts dropped."""
    while scope.endswith("}") and "{" in scope.rsplit(".", 1)[-1]:
        scope = scope.rpartition(".")[0]
    return scope


def _js_words(code, word):
    """Offsets where word occurs as a whole word (not a member name)."""
    found, at = [], code.find(word)
    while at >= 0:
        end = at + len(word)
        if (not at or not (code[at - 1].isalnum() or code[at - 1] in "_$.")) and \
                (end >= len(code) or not (code[end].isalnum() or code[end] in "_$")):
            found.append(at)
        at = code.find(word, end)
    return found


def _js_record(text):
    """Units for find, and definitions, imports, calls, references and written types for callers."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    code, strings, comments = _js_mask(text)
    lines = code.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    count = max(1, len(lines))
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line) + 1
    breaks = [match.start() for match in re.finditer("\n", code)]

    def line_of(at):
        return bisect.bisect_left(breaks, at) + 1

    # Declaration candidates (one per line start) and call candidates (one per "(").
    decls = []
    for number, line in enumerate(lines, 1):
        if not line or line.isspace():
            continue
        match = _JS_DECL.match(line)
        if match:
            decls.append((starts[number - 1] + len(line) - len(line.lstrip()), number, match))
    reverse, total, calls = code[::-1], len(code), []
    for match in re.finditer(r"\(", code):
        at = match.start()
        found = _JS_CALL_REV.match(reverse, total - at)
        if not found:
            continue
        chain_start, chain_end = found.span("chain")
        forward = code[total - chain_end:total - chain_start]
        parts = [part for part in re.split(r"\s*\??!?\s*\.\s*\??\s*", forward.strip())]
        if not parts or any(not part or part.lstrip("#")[:1].isdigit() for part in parts):
            continue
        lead = found.group("lead").strip()[::-1]
        if lead in ("function", "get", "set", "async", "static"):
            continue
        if len(parts) == 1 and parts[0] in _JS_KEYWORDS:
            continue
        name_at = total - chain_start - len(parts[-1])
        chain = ".".join(parts)
        receiver = None
        dot = total - found.end("lead")
        if lead.startswith(".") and code[max(0, dot - 2):dot] == "..":  # ...spread, not a receiver
            lead = ""
        if lead.startswith("."):
            chain = "?." + chain
            receiver = total - found.end("lead") - 1  # the receiver ends here (whitespace allowed)
            while receiver > 0 and code[receiver] in " \t\n":
                receiver -= 1
            receiver = receiver if code[receiver] == ")" else None
        calls.append((name_at, at, chain, receiver))
    points = sorted([start for start, _, _ in decls] + [call[0] for call in calls])
    pairs, around_list = _js_brackets(code, points)
    around = dict(zip(points, around_list))
    if any(call[3] is not None for call in calls):  # a.b().c(: the receiver is what a.b() returns
        opens, chains = {close: opening for opening, close in pairs.items()}, {}
        for index, (name_at, at, chain, receiver) in enumerate(calls):
            if receiver is not None and opens.get(receiver) in chains:
                inner = chains[opens[receiver]]
                if not inner.startswith("?"):
                    chain = inner + "()." + chain[2:]
                    calls[index] = (name_at, at, chain, receiver)
            chains[at] = chain

    defs, extra, names_at = [], [], set()  # extra[i]: (start, end, body) offsets of defs[i]
    types, bases, implements, exports = [], {}, {}, []
    class_bodies, interface_bodies, stack, params_of = {}, {}, [], {}
    position, bodies, blocks, spans = {}, set(), {}, []  # spans: (start, end, scope) of let/const blocks

    def parent_at(at):
        while stack and stack[-1][1] < at:
            stack.pop()
        return stack[-1] if stack else None

    def add(qualname, kind, start, end, body=None, name_at=None):
        index = position.get(qualname)
        if index is not None:
            if body is None or extra[index][2] is not None:
                return False
            defs[index][1:] = [kind, line_of(start), line_of(end)]
            extra[index] = (start, end, body)
        else:
            position[qualname] = len(defs)
            defs.append([qualname, kind, line_of(start), line_of(end)])
            extra.append((start, end, body))
        if name_at is not None:
            names_at.add(name_at)
        if body is not None:
            bodies.add(body)
        stack.append((start, end, qualname, kind))
        return True

    def add_params(owner, opening, close, is_constructor=False, cls=None):
        for name, kind, is_property in _js_params(code[opening + 1:close]):
            params_of.setdefault(owner, []).append(name)
            types.append([owner, name, kind or "?"])  # "?": a local name whose type is not written
            if kind and is_constructor and is_property and cls:
                types.append([cls, "this." + name, kind])

    def add_value_params(qualname, value):
        if value[1] is not None:
            add_params(qualname, value[1], pairs[value[1]])
        elif len(value) > 4:
            params_of.setdefault(qualname, []).append(value[4])
            types.append([qualname, value[4], "?"])

    def add_class(qualname, header_at, start, export_default=False, exported=False):
        body = _js_body(code, header_at, pairs, header=True)
        if body is None or body not in pairs:
            return
        header = code[header_at:body]
        extends = re.search(r"\bextends\s+([A-Za-z_$][\w$]*(?:\s*\.\s*[A-Za-z_$][\w$]*)*)", header)
        if extends:
            bases[qualname] = [re.sub(r"\s+", "", extends.group(1))]
        clause = re.search(r"\bimplements\s+(.*)$", header, re.S)
        if clause:
            implements[qualname] = [kind for kind in map(_js_type, _js_split(clause.group(1))) if kind]
        if add(qualname, "class", start, pairs[body], body):
            class_bodies[body] = qualname
            if export_default:
                exports.append(["default", qualname])
            elif exported:
                exports.append([qualname, qualname])

    for start, number, match in decls:
        enclosing = around.get(start, -1)
        bracket = code[enclosing] if enclosing >= 0 else ""
        parent = parent_at(start)
        prefix = parent[2] + "." if parent else ""
        mods = match.group("mods") or ""
        default = "default" in mods.split()
        exported = "export" in mods.split()
        if match.group("mname") is not None:
            owner = class_bodies.get(enclosing)
            if owner is None and enclosing not in interface_bodies:
                continue
            if owner is None:  # an interface member: method signatures only
                if match.group("after") in "(<":
                    opening = _js_skip(code, _js_generics(code, match.start("after") + starts[number - 1]))
                    close = pairs.get(opening)
                    if close is not None and add(interface_bodies[enclosing] + "." + match.group("mname"), "method",
                                                 start, close, name_at=starts[number - 1] + match.start("mname")):
                        stack.pop()
                        returns = _js_returns(code, close, None)
                        if returns:
                            types.append([interface_bodies[enclosing] + "." + match.group("mname"), "()", returns])
                continue
            name, after = match.group("mname"), match.group("after")
            qualname = owner + "." + name
            name_at = starts[number - 1] + match.start("mname")
            after_at = starts[number - 1] + match.start("after")
            if after in "(<":
                opening = _js_skip(code, _js_generics(code, after_at))
                close = pairs.get(opening) if opening < len(code) and code[opening] == "(" else None
                if close is None:
                    continue
                body = _js_body(code, close + 1, pairs)
                end = pairs.get(body, close) if body is not None else close
                if add(qualname, "method", start, end, body, name_at):
                    add_params(qualname, opening, close, name == "constructor", owner)
                    returns = _js_returns(code, close, body)
                    if returns:
                        types.append([qualname, "()", returns])
                continue
            annotation, value_at = (None, after_at + 1) if after == "=" else (
                _js_type_and_value(code, after_at, pairs) if after == ":" else (None, None))
            kind = _js_type(annotation)
            value = _js_value(code, value_at, pairs) if value_at is not None else None
            if value and value[0] == "new":
                kind = value[1]
            elif value and value[0] == "call":
                kind = kind or value[1]
            if kind:
                types.append([owner, "this." + name, kind])
            if value and value[0] == "function":
                if add(qualname, "method", start, value[3], value[2], name_at):
                    add_value_params(qualname, value)
            else:
                end = _js_end(code, value_at, pairs) if value_at is not None else after_at
                if add(qualname, "variable", start, end, None, name_at):
                    stack.pop()
            continue
        if enclosing >= 0 and (bracket != "{" or enclosing in class_bodies or enclosing in interface_bodies):
            continue
        if parent and parent[3] in ("interface", "enum", "type"):
            continue
        line_at = starts[number - 1]
        keyword = match.group("kw")
        if keyword == "function":
            name = match.group("kname") or ("default" if default else None)
            if not name:
                continue
            after = match.end("kname") if match.group("kname") else match.end()
            opening = _js_skip(code, _js_generics(code, _js_skip(code, line_at + after)))
            close = pairs.get(opening) if opening < len(code) and code[opening] == "(" else None
            if close is None:
                continue
            body = _js_body(code, close + 1, pairs)
            name_at = line_at + match.start("kname") if match.group("kname") else None
            if add(prefix + name, "function", start, pairs.get(body, close) if body is not None else close, body,
                   name_at):
                add_params(prefix + name, opening, close)
                returns = _js_returns(code, close, body)
                if returns:
                    types.append([prefix + name, "()", returns])
                if default:  # an anonymous default function is the definition named "default"
                    exports.append(["default", prefix + name])
                elif exported and not parent:
                    exports.append([name, name])
            continue
        if keyword == "class":
            name = match.group("kname")
            if name in (None, "extends", "implements"):
                name = "default" if default else None
                header_at = line_at + match.start("kname") if match.group("kname") else line_at + match.end()
            else:
                header_at = line_at + match.end("kname")
                names_at.add(line_at + match.start("kname"))
            if name:
                add_class(prefix + name, header_at, start, default, exported and not parent)
            continue
        if match.group("lhs"):
            name = match.group("xname") or match.group("lhs").rsplit(".", 1)[-1]
            header_at = line_at + (match.end("xname") if match.group("xname") else match.end())
            add_class(prefix + name, header_at, start)
            continue
        if match.group("cname") or match.group("pname"):
            name = match.group("cname") or match.group("pname")
            qualname = name if match.group("cname") else match.group("owner") + "." + name
            value_at = line_at + match.end()
            value = _js_value(code, value_at, pairs)
            if value and value[0] == "function":
                if add(qualname, "function" if match.group("cname") else "method", start, value[3], value[2]):
                    add_value_params(qualname, value)
            elif match.group("cname") and not parent:
                if add(qualname, "variable", start, _js_end(code, value_at, pairs)):
                    stack.pop()
            if match.group("cname"):
                exports.append([name, qualname])
            continue
        keyword, name = match.group("kw2"), match.group("name2")
        if keyword is None:
            continue
        if keyword in ("let", "const") and bracket == "{" and enclosing not in bodies and enclosing in pairs:
            # let/const in a block that is not a function body: a scope of its own, named "{line}"
            if enclosing not in blocks:
                blocks[enclosing] = f"{prefix}{{{line_of(enclosing)}}}"
                spans.append((enclosing, pairs[enclosing], blocks[enclosing]))
                stack.append((enclosing, pairs[enclosing], blocks[enclosing], "block"))
            parent = (enclosing, pairs[enclosing], blocks[enclosing], "block")
            prefix = blocks[enclosing] + "."
        name_at = line_at + match.start("name2")
        if keyword in ("interface", "enum") or keyword.startswith("const") and keyword.endswith("enum"):
            body = _js_body(code, line_at + match.end("name2"), pairs, header=True)
            if body is None or body not in pairs:
                continue
            kind = "interface" if keyword == "interface" else "enum"
            if kind == "interface":
                extends = re.search(r"\bextends\s+(.*)$", code[line_at + match.end("name2"):body], re.S)
                if extends:
                    bases[prefix + name] = [kind for kind in map(_js_type, _js_split(extends.group(1))) if kind]
            if add(prefix + name, kind, start, pairs[body], body, name_at):
                if kind == "interface":
                    interface_bodies[body] = prefix + name
                if exported and not parent:
                    exports.append([name, name])
            continue
        if keyword in ("namespace", "module"):
            body = _js_body(code, line_at + match.end("name2"), pairs, header=True)
            if body is not None and body in pairs and add(prefix + name, "namespace", start, pairs[body], body, name_at) \
                    and exported and not parent:
                exports.append([name, name])
            continue
        if keyword == "type":
            equals = code.find("=", line_at + match.end("name2"))
            if equals < 0:
                continue
            if add(prefix + name, "type", start, _js_end(code, equals + 1, pairs), None, name_at):
                stack.pop()
                if exported and not parent:
                    exports.append([name, name])
            continue
        if "." in name:
            continue
        annotation, value_at = _js_type_and_value(code, line_at + match.end("name2"), pairs)
        kind = _js_type(annotation)
        value = _js_value(code, value_at, pairs) if value_at is not None else None
        scope = parent[2] if parent else ""
        if value and value[0] == "new":
            kind = value[1]
        elif value and value[0] == "call":
            kind = kind or value[1]
        if kind:
            types.append([scope, name, kind])
        elif parent and parent[3] != "namespace" and not (value and value[0] in ("function", "class")) and not (
                value_at is not None and _JS_BINDS_MODULE.match(code, value_at)):
            types.append([scope, name, "?"])  # a local variable shadows an import of the same name
        if exported and not parent:
            exports.append([name, name])
        if value and value[0] == "function":
            if add(prefix + name, "function", start, value[3], value[2], name_at):
                add_value_params(prefix + name, value)
        elif value and value[0] == "class":
            add_class(prefix + name, value[2], start)
        elif not parent or parent[3] == "namespace":
            end = _js_end(code, value_at, pairs) if value_at is not None else line_at + match.end()
            if add(prefix + name, "variable", start, end, None, name_at):
                stack.pop()
                if default:
                    exports.append(["default", prefix + name])

    # Scopes: the innermost definition around each call, import and reference.
    order = sorted([(extra[index][0], extra[index][1], defs[index][0]) for index in range(len(defs))
                    if defs[index][1] != "variable"] + spans, key=lambda span: (span[0], -span[1]))

    def scopes(offsets):
        found, open_spans, pointer = [], [], 0
        for at in offsets:
            while pointer < len(order) and order[pointer][0] <= at:
                span = order[pointer]
                while open_spans and open_spans[-1][1] < span[0]:
                    open_spans.pop()
                open_spans.append(span)
                pointer += 1
            while open_spans and open_spans[-1][1] < at:
                open_spans.pop()
            found.append(open_spans[-1][2] if open_spans else "")
        return found

    kinds = {qualname: defs[index][1] for qualname, index in position.items()}
    kept = []
    for name_at, at, chain, _receiver in calls:
        if name_at in names_at:
            continue
        enclosing = around.get(name_at, -1)
        if enclosing in interface_bodies:
            continue
        close = pairs.get(at)
        if close is not None:
            after = _js_skip(code, close + 1)
            if after < len(code) and code[after] == "{" and not chain.startswith("?."):
                continue  # object-literal method shorthand: name(args) { ... }
            if after < len(code) and code[after] == ":" and "." not in chain:
                before = code[code.rfind("\n", 0, name_at) + 1:name_at]
                if _JS_MODIFIERS_ONLY.fullmatch(before) or before.rstrip()[-1:] in ("{", ";", ","):
                    continue  # a method signature in a type literal: name(args): Type
        kept.append((name_at, chain))
    call_scopes = scopes([name_at for name_at, _ in kept])
    calls_out = [[line_of(name_at), scope, chain] for (name_at, chain), scope in zip(kept, call_scopes)
                 if kinds.get(scope) not in ("type", "interface")]
    assigned = list(_JS_THIS_NEW.finditer(code))
    for match, scope in zip(assigned, scopes([match.start() for match in assigned])):
        owner = scope
        while owner and kinds.get(owner) != "class":
            owner = owner.rpartition(".")[0]
        if owner:
            types.append([owner, "this." + match.group(1), re.sub(r"\s+", "", match.group(2))])

    # Imports and exports.
    imports, taken = [], set()

    def spec(match):
        found = strings.get(match.start("q"))
        if found is None or not found[1] or len(found[1]) > 300:
            return None
        taken.add(match.start("q"))
        return found[1]

    import_sites, at_import, at_export = [], _js_words(code, "import"), _js_words(code, "export")
    for match in filter(None, (_JS_IMPORT_EQUALS.match(code, at) for at in at_import)):
        target = spec(match)
        if target:
            import_sites.append((match.start(), target, "require", None, match.group("local")))
    for match in filter(None, (_JS_IMPORT.match(code, at) for at in at_import)):
        target = spec(match)
        if target is None:
            continue
        clause = match.group("clause").strip()
        rest = clause
        head = re.match(r"([A-Za-z_$][\w$]*)\s*(?:,|$)", clause)
        if head and head.group(1) != "type":
            import_sites.append((match.start(), target, "default", "default", head.group(1)))
            rest = clause[head.end():]
        namespace = re.search(r"\*\s*as\s+([A-Za-z_$][\w$]*)", rest)
        if namespace:
            import_sites.append((match.start(), target, "namespace", None, namespace.group(1)))
        braces = re.search(r"\{([^{}]*)\}", rest)
        if braces:
            for item in braces.group(1).split(","):
                specifier = _JS_SPECIFIER.fullmatch(item.strip())
                if specifier:
                    import_sites.append((match.start(), target, "named", specifier.group(1),
                                         specifier.group(2) or specifier.group(1)))
        if not head and not namespace and not braces:
            import_sites.append((match.start(), target, "side", None, None))
    for match in filter(None, (_JS_REEXPORT.match(code, at) for at in at_export)):
        target = spec(match)
        if target is None:
            continue
        clause = match.group("clause")
        if clause.startswith("*"):
            alias = re.search(r"as\s+([A-Za-z_$][\w$]*)", clause)
            import_sites.append((match.start(), target, "reexport-namespace" if alias else "reexport-all", None,
                                 alias.group(1) if alias else None))
            continue
        for item in clause.strip("{} \n\t").split(","):
            specifier = _JS_SPECIFIER.fullmatch(item.strip())
            if specifier:
                import_sites.append((match.start(), target, "reexport", specifier.group(1),
                                     specifier.group(2) or specifier.group(1)))
    for match in filter(None, (_JS_REQUIRE.match(code, at) for at in _js_words(code, "require"))):
        if match.start("q") in taken:
            continue
        target = spec(match)
        if target is None:
            continue
        binding = _JS_REQUIRE_BIND.search(code, max(0, match.start() - 300), match.start())
        bind = binding.group(1) if binding else None
        if not bind:
            import_sites.append((match.start(), target, "side", None, None))
        elif bind.startswith("{"):
            for item in bind.strip("{} \n\t").split(","):
                pair = re.fullmatch(r"\s*([\w$]+)\s*(?::\s*([\w$]+))?\s*", item)
                if pair:
                    import_sites.append((match.start(), target, "named", pair.group(1), pair.group(2) or pair.group(1)))
        else:
            import_sites.append((match.start(), target, "require", None, bind))
    for match in filter(None, (_JS_DYNAMIC.match(code, at) for at in at_import)):
        target = spec(match)
        if target is not None:
            import_sites.append((match.start(), target, "dynamic", None, None))
    for match in filter(None, (_JS_IMPORT_SIDE.match(code, at) for at in at_import)):
        if match.start("q") not in taken:
            target = spec(match)
            if target is not None:
                import_sites.append((match.start(), target, "side", None, None))
    import_sites.sort()
    import_scopes = scopes([site[0] for site in import_sites])
    for (at, target, kind, imported, local), scope in zip(import_sites, import_scopes):
        imports.append([line_of(at), scope, target, kind, imported, local])
    for match in filter(None, (_JS_EXPORT_LIST.match(code, at) for at in at_export)):
        for item in match.group("list").split(","):
            specifier = _JS_SPECIFIER.fullmatch(item.strip())
            if specifier:
                exports.append([specifier.group(2) or specifier.group(1), specifier.group(1)])
    for match in filter(None, (_JS_EXPORT_DEFAULT.match(code, at) for at in at_export)):
        exports.append(["default", match.group("name")])
    for match in filter(None, (_JS_EXPORT_ASSIGN.match(code, at) for at in at_export + [
            at for at in _js_words(code, "module") if code.startswith("module.exports", at)])):
        if match.group("name"):
            exports.append(["default", match.group("name")])
        elif match.start("obj") in pairs:
            body = code[match.start("obj") + 1:pairs[match.start("obj")]]
            for item in _js_split(body):
                pair = re.fullmatch(r"\s*([A-Za-z_$][\w$]*)\s*(?::\s*([A-Za-z_$][\w$]*)\s*)?", item)
                if pair:
                    exports.append([pair.group(1), pair.group(2) or pair.group(1)])

    # References: dotted names whose head an import binds (ns.Name, mod.func passed as a value).
    refs = []
    bound = sorted({site[4] for site in import_sites if site[4] and site[2] in ("namespace", "require", "default")})
    if bound:
        pattern = re.compile(r"(?<![\w$.#])(?:" + "|".join(map(re.escape, bound)) + r")(?:\s*\??\.\s*#?[A-Za-z_$][\w$]*)+"
                             r"(?![\w$])(?!\s*(?:<[^<>()\n]*>)?\s*\()")
        found = list(pattern.finditer(code))
        for match, scope in zip(found, scopes([match.start() for match in found])):
            refs.append([line_of(match.start()), scope, re.sub(r"[\s?]", "", match.group())])

    # Units for find: one per definition, words weighted like Python's.
    units = [_new_unit("", "module", 1, 1, count)]
    unit_of = {}
    for index, (qualname, kind, line, end) in enumerate(defs):
        start_line = line
        while start_line > 1 and lines[start_line - 2].lstrip().startswith("@"):
            start_line -= 1
        unit = _new_unit(_plain_scope(qualname), kind, line, start_line, max(end, line))
        body = extra[index][2]
        unit.append(line_of(body) if body is not None else line)
        name = qualname.rsplit(".", 1)[-1].lstrip("#")
        _add_ident(unit[6], name, W_NAME)
        for part in _plain_scope(qualname).split(".")[:-1]:
            _add_ident(unit[6], part, W_QUAL)
        unit_of[qualname] = len(units)
        units.append(unit)
    owner = _owner_map(units, count)
    unit_starts = {}
    for index, unit in enumerate(units[1:], 1):
        unit_starts.setdefault(unit[3], index)
    text_breaks = [match.start() for match in re.finditer("\n", text)]
    raw_lines = text.split("\n")
    for at, raw in comments:
        first = bisect.bisect_left(text_breaks, at) + 1
        last = first + raw.count("\n")
        body = raw[2:-2] if raw.startswith("/*") else raw[2:]
        index = owner[first] if first < len(owner) else 0
        if not text[text.rfind("\n", 0, at) + 1:at].strip():  # a whole-line comment describes what follows it
            following = last + 1
            while following <= len(raw_lines) and raw_lines[following - 1].lstrip().startswith(("//", "/*", "*")):
                following += 1
            target = unit_starts.get(following)
            if target is not None:
                if raw.startswith("/**") and not units[target][5]:
                    units[target][5] = _first_line(re.sub(r"(?m)^\s*\*+ ?", "", body).replace("@", " "))
                _add_text(units[target][6], body[:8000], W_DOC if raw.startswith("/**") else W_COMMENT)
                continue
        _add_text(units[index][6], body[:8000], W_COMMENT)
    for at, value in strings.values():
        if value:
            number = bisect.bisect_left(text_breaks, at) + 1
            _add_text(units[owner[number] if number < len(owner) else 0][6], value[:4000], W_STRING)
    for number, line in enumerate(lines, 1):
        if line and not line.isspace():
            terms = units[owner[number]][6]
            for ident in _IDENT.findall(line):
                if ident not in _JS_NOISE:
                    for term in _ident_terms(ident):
                        terms[term] = terms.get(term, 0.0) + W_IDENT
    for qualname, names in params_of.items():
        if qualname in unit_of:
            for name in names:
                _add_ident(units[unit_of[qualname]][6], name, W_PARAM)
    js = {"defs": defs, "imports": imports, "calls": calls_out, "refs": refs, "bases": bases,
          "implements": implements, "types": types, "exports": exports}
    if text.startswith("#!") and "node" in text[:text.find("\n") if "\n" in text else len(text)]:
        js["main"] = 1
    return units, js


def _kind(path, data):
    suffix = os.path.splitext(path)[1].lower()
    if suffix in KINDS:
        return KINDS[suffix]
    first = data[:120].split(b"\n", 1)[0]
    if first.startswith(b"#!"):
        if b"python" in first:
            return "python"
        if re.search(rb"\b(?:ba|z|da|k)?sh\b", first):
            return "shell"
    return "text"


_JSONC = re.compile(r'"(?:[^"\\\n]|\\.)*"|//[^\n]*|/\*.*?\*/', re.S)


def _jsonc(text):
    """Parse JSON with comments and trailing commas (tsconfig.json, jsconfig.json); None if it does not parse."""
    stripped = _JSONC.sub(lambda match: match.group() if match.group().startswith('"') else " ", text)
    stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)
    try:
        return json.loads(stripped)
    except ValueError:
        return None


def _json_facts(path, text):
    """Module-resolution settings of tsconfig/jsconfig files (and of any JSON file with compilerOptions or
    extends, which a tsconfig may extend) and entry points of package.json files."""
    name = path.rsplit("/", 1)[-1]
    if name != "package.json" and (re.fullmatch(r"(?:ts|js)config(?:\.[\w.-]+)?\.json", name)
                                   or '"compilerOptions"' in text or '"extends"' in text):
        data = _jsonc(text)
        if isinstance(data, dict) and (re.fullmatch(r"(?:ts|js)config(?:\.[\w.-]+)?\.json", name)
                                       or isinstance(data.get("compilerOptions"), dict) or "extends" in data):
            options = data.get("compilerOptions") if isinstance(data.get("compilerOptions"), dict) else {}
            paths = options.get("paths") if isinstance(options.get("paths"), dict) else {}
            config = {"baseUrl": options.get("baseUrl") if isinstance(options.get("baseUrl"), str) else None,
                      "paths": {key: [item for item in value if isinstance(item, str)]
                                for key, value in paths.items() if isinstance(value, list)},
                      "extends": data.get("extends") if isinstance(data.get("extends"), (str, list)) else None}
            return {"tsconfig": config}
    elif name == "package.json":
        data = _jsonc(text)
        if isinstance(data, dict):
            entry = {key: data[key] for key in ("name", "main", "module", "bin")
                     if isinstance(data.get(key), str) or (key == "bin" and isinstance(data.get(key), dict))}
            if isinstance(entry.get("bin"), dict):
                entry["bin"] = {key: value for key, value in entry["bin"].items() if isinstance(value, str)}
            lines = {}
            for number, line in enumerate(_lines(text), 1):
                found = re.match(r'\s*"(main|module|bin)"\s*:', line)
                if found and found.group(1) in entry:
                    lines.setdefault(found.group(1), number)
            if lines:
                entry["lines"] = lines
            return {"package": entry} if entry else {}
    return {}


def extract(path, data):
    """Index one file's bytes: its kind, search units and (for Python) definitions, imports and calls."""
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    kind = _kind(path, data)
    text = data.decode("utf-8", errors="replace")
    lines = _lines(text)
    python, script, error, facts = None, None, None, {}
    if kind == "python":
        try:
            units, python = _python_record(lines, text)
        except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
            kind, error = "python-regex", f"{type(exc).__name__}: {getattr(exc, 'msg', None) or exc}"[:160]
            if getattr(exc, "lineno", None):
                error += f" (line {exc.lineno})"
            units, python = _python_fallback(lines)
    elif kind == "javascript":
        try:
            units, script = _js_record(text)
        except (ValueError, IndexError, KeyError, RecursionError, MemoryError) as exc:  # a scanner bug: keep the file
            error = f"{type(exc).__name__}: {exc}"[:160]
            units = _other_units(kind, lines)
    else:
        units = _other_units(kind, lines)
        if kind == "json":
            facts = _json_facts(path, text)
    kept = []
    for index, unit in enumerate(units):
        if not unit[6] and not unit[0] and index:
            continue
        unit[6] = {term: round(weight, 2) for term, weight in unit[6].items()}
        unit[7] = round(sum(unit[6].values()), 1)
        kept.append(unit)
    record = {"kind": kind, "lines": len(lines), "units": kept}
    record.update(facts)
    if python is not None:
        record["py"] = python
    if script is not None:
        record["js"] = script
    if error:
        record["error"] = error
    return record


# ---------------------------------------------------------------- building and caching


def _lstat_link(path):
    try:
        info = os.lstat(path)
    except OSError:
        return True
    return stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", 0) in LINK_TAGS


def _generated_paths(directory):
    """Paths that sync_examples.py generated in this directory, if its manifest says so."""
    marker = os.path.join(directory, *GENERATED_MARKER)
    if not os.path.isfile(marker):
        return None
    try:
        with open(marker, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(manifest, dict) or not str(manifest.get("installation_id", "")).startswith(GENERATED_PREFIX):
        return None
    managed = manifest.get("managed_files")
    return frozenset(list(managed if isinstance(managed, dict) else ()) + ["/".join(GENERATED_MARKER)])


def _walk(root, counts, include_generated=False, cache_dir=None):
    """Yield (relative POSIX path, absolute path, stat) for each regular file worth indexing."""
    marks = []
    cache_key = os.path.normcase(cache_dir) if cache_dir else None
    for current, dirnames, filenames in os.walk(root):
        relative = os.path.relpath(current, root).replace(os.sep, "/")
        prefix = "" if relative == "." else relative + "/"
        kept = []
        for name in dirnames:
            full = os.path.join(current, name)
            if (name in SKIP_DIRS or name.endswith(".egg-info") or os.path.normcase(full) == cache_key
                    or _lstat_link(full) or os.path.isfile(os.path.join(full, "pyvenv.cfg"))):
                counts["skipped directories"] += 1
                continue
            kept.append(name)
        dirnames[:] = sorted(kept)
        if not include_generated:
            generated = _generated_paths(current)
            if generated:
                marks.append((prefix, generated))
        in_cache = os.path.normcase(current) == cache_key
        for name in sorted(filenames):
            path = prefix + name
            if name == ".git" or (in_cache and name.startswith(("code-index-", ".code-index-"))):
                continue
            if any(path.startswith(mark) and path[len(mark):] in generated for mark, generated in marks):
                counts["generated copies"] += 1
                continue
            if os.path.splitext(name)[1].lower().lstrip(".") in BINARY_SUFFIXES:
                counts["binary"] += 1
                continue
            full = os.path.join(current, name)
            try:
                info = os.lstat(full)
            except OSError:
                continue
            if not stat.S_ISREG(info.st_mode) or getattr(info, "st_reparse_tag", 0) in LINK_TAGS:
                counts["links"] += 1
                continue
            yield path, full, info


def _ctime(info):
    """Inode change time on POSIX (any write or metadata change moves it, and it cannot be set back); None
    on Windows, where st_ctime is the creation time."""
    return None if os.name == "nt" else info.st_ctime_ns


def default_cache_dir():
    """The user's local cache directory for indexes: $XDG_CACHE_HOME/oaw/code-index or ~/.cache/oaw/code-index,
    %LOCALAPPDATA%\\oaw\\code-index on Windows; None when no absolute location is known."""
    if os.name == "nt":
        import ntpath
        base = os.environ.get("LOCALAPPDATA") or ntpath.join(os.path.expanduser("~"), "AppData", "Local")
        return ntpath.join(base, "oaw", "code-index") if ntpath.isabs(base) else None
    base = os.environ.get("XDG_CACHE_HOME") or ""
    if not os.path.isabs(base):
        base = os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "oaw", "code-index") if os.path.isabs(base) else None


def _inside(path, root):
    try:
        relative = os.path.relpath(os.path.abspath(path), os.path.abspath(root))
    except ValueError:  # another Windows drive
        return False
    return relative == "." or not (relative == ".." or relative.startswith(".." + os.sep))


def choose_cache(root, cache=None, no_cache=False):
    """(cache directory or None, where it came from) for the command line: --no-cache, --cache, the
    environment variable, else the user's local cache directory unless that lies inside the indexed tree."""
    if no_cache:
        return None, "none"
    if cache:
        return cache, "--cache"
    if os.environ.get(CACHE_ENV):
        return os.environ[CACHE_ENV], CACHE_ENV
    default = default_cache_dir()
    if default is None or _inside(default, root):
        return None, "none"
    return default, "default"


def _engine():
    """Fingerprint of this file: a cache written by other indexing code is rebuilt, not trusted."""
    try:
        with open(__file__, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()[:16]
    except (OSError, NameError):
        return str(INDEX_VERSION)


ENGINE = _engine()


def _cache_file(root, cache_dir):
    digest = hashlib.sha256(os.path.normcase(root).encode("utf-8", "surrogatepass")).hexdigest()[:16]
    return os.path.join(cache_dir, f"code-index-{digest}.json")


def _units_file(cache_path):
    """Search units live beside the main cache file, so that callers, affected, path and overview never load
    them; both files carry the same token, written units first."""
    return cache_path[:-len(".json")] + ".units.json"


def _load_cache(path, root, include_generated, need_units):
    """(files, token, units loaded) from a matching cache, or None."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if (not isinstance(data, dict) or data.get("index_version") != INDEX_VERSION or data.get("root") != root
            or data.get("engine") != ENGINE or data.get("include_generated") != include_generated
            or not isinstance(data.get("files"), dict)):
        return None
    token = data.get("token")
    if need_units:
        return (data["files"], token, True) if _attach_units(path, token, data["files"]) else None
    try:
        with open(_units_file(path), encoding="utf-8") as handle:
            head = handle.read(200)
    except OSError:
        return None
    found = re.match(r'\{"token":"([0-9a-f]+)"', head)
    return (data["files"], token, False) if found and found.group(1) == token else None


def _attach_units(path, token, files):
    """Put each record's search units back from the units file; False when it is missing or does not match."""
    try:
        with open(_units_file(path), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict) or data.get("token") != token or not isinstance(data.get("files"), dict):
        return False
    units = data["files"]
    for name, record in files.items():
        entry = units.get(name)
        if isinstance(entry, dict) and "units" in entry and isinstance(record, dict):
            record["units"] = entry["units"]
    return True


def _write_json(path, data):
    handle, temporary = tempfile.mkstemp(prefix=".code-index-", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, separators=(",", ":"), ensure_ascii=False)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _save_cache(path, root, include_generated, files):
    token = os.urandom(8).hex()
    _write_json(_units_file(path), {"token": token, "files": {
        name: {"units": record["units"]} for name, record in files.items() if "units" in record}})
    _write_json(path, {"token": token, "index_version": INDEX_VERSION, "engine": ENGINE, "root": root,
                       "include_generated": include_generated,
                       "files": {name: {key: value for key, value in record.items() if key != "units"}
                                 for name, record in files.items()}})


PARALLEL_MIN_FILES = 200  # fewer files to (re-)index are done in this process
MAX_JOBS = 8


def _extract_item(item):
    return extract(*item)


def _extract_all(todo):
    """{path: record} for [(path, bytes)]; in worker processes (standard library) when there are many."""
    jobs = min(MAX_JOBS, os.cpu_count() or 1)
    if len(todo) >= PARALLEL_MIN_FILES and jobs > 1:
        try:
            import concurrent.futures
            with concurrent.futures.ProcessPoolExecutor(jobs) as pool:
                return dict(zip((path for path, _ in todo), pool.map(_extract_item, todo, chunksize=16)))
        except (OSError, ImportError, NotImplementedError, RuntimeError):  # no process support: one process
            pass
    return {path: extract(path, data) for path, data in todo}


def build_index(root=".", cache_dir=None, frozen=False, include_generated=False, need_units=True):
    """Index root (on the fly, or through the cache in cache_dir) and return an Index. need_units=False
    leaves out the search units that only find uses, when the cache can supply everything else."""
    started = time.perf_counter()
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise CodeIndexError(f"root is not a directory: {root}")
    cache_path, old, token, units_loaded = None, None, None, True
    if cache_dir:
        cache_dir = os.path.abspath(cache_dir)
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except OSError as exc:
            raise CodeIndexError(f"cannot create cache directory {cache_dir}: {exc.strerror or exc}") from None
        cache_path = _cache_file(root, cache_dir)
        loaded = _load_cache(cache_path, root, include_generated, need_units)
        if loaded:
            old, token, units_loaded = loaded
    counts, files, stale, todo, details = Counter(), {}, [], [], {}
    for path, full, info in _walk(root, counts, include_generated, cache_dir):
        previous = old.get(path) if old else None
        if previous and previous.get("size") == info.st_size and previous.get("mtime_ns") == info.st_mtime_ns \
                and previous.get("ctime_ns") == _ctime(info):
            files[path] = previous
            counts["reused"] += 1
            continue
        if frozen and old is not None:
            stale.append(path)
            if previous:
                files[path] = previous
            continue
        if info.st_size > MAX_FILE_BYTES:
            files[path] = {"kind": "skipped", "reason": "over 1 MB", "size": info.st_size,
                           "mtime_ns": info.st_mtime_ns, "ctime_ns": _ctime(info), "sha256": None}
            counts["indexed"] += 1
            continue
        try:
            with open(full, "rb") as handle:
                data = handle.read(MAX_FILE_BYTES + 1)
        except OSError:
            counts["unreadable"] += 1
            continue
        digest = hashlib.sha256(data).hexdigest()
        if previous and previous.get("sha256") == digest:
            previous["mtime_ns"], previous["size"], previous["ctime_ns"] = info.st_mtime_ns, info.st_size, _ctime(info)
            files[path] = previous
            counts["reused"] += 1
            counts["touched"] += 1
            continue
        details[path] = dict(size=info.st_size, mtime_ns=info.st_mtime_ns, ctime_ns=_ctime(info), sha256=digest)
        files[path] = None
        if b"\0" in data[:8192]:
            files[path] = {"kind": "skipped", "reason": "binary"}
        else:
            todo.append((path, data))
        counts["indexed"] += 1
    removed = sorted(set(old or ()) - set(files) - set(stale))
    if frozen:
        stale.extend(path for path in removed if path not in stale)
    write = cache_path and (counts["indexed"] or counts["touched"] or removed or old is None) and not (frozen and old)
    if write and not units_loaded and not _attach_units(cache_path, token, files):
        for path, record in files.items():  # units file lost since loading: index those files again
            if record is not None and "units" not in record and record.get("kind") != "skipped":
                with open(os.path.join(root, *path.split("/")), "rb") as handle:
                    todo.append((path, handle.read(MAX_FILE_BYTES + 1)))
                details[path] = {key: record[key] for key in ("size", "mtime_ns", "ctime_ns", "sha256")}
    for path, record in _extract_all(todo).items():
        files[path] = record
    for path, detail in details.items():
        files[path].update(detail)
    if write:
        try:
            _save_cache(cache_path, root, include_generated, files)
        except OSError as exc:
            raise CodeIndexError(f"cannot write cache {cache_path}: {exc.strerror or exc}") from None
    info = {"seconds": time.perf_counter() - started, "cache": cache_path, "counts": dict(counts),
            "removed": len(removed), "stale": sorted(stale), "frozen": bool(frozen and old is not None)}
    return Index(root, files, info)


# ---------------------------------------------------------------- the loaded index


class Index:
    """Indexed records plus the lazily built name tables that callers, path and affected use."""

    def __init__(self, root, files, info):
        self.root, self.files, self.info = root, files, info
        self._tables = None
        self._modules = {}
        self._bindings = {}
        self._edges = None
        self._dirs = None
        self._js_modules = {}
        self._configs = {}
        self._scoped = {}

    # -------- paths and modules

    def tables(self):
        if self._tables is None:
            defs, by_name, module_names, var_types, classes = {}, {}, {}, {}, {}
            js_types, js_bases, js_implements, js_exports = {}, {}, {}, {}
            for path, record in self.files.items():
                script = record.get("js")
                if script:
                    for qualname, kind, line, end in script["defs"]:
                        defs.setdefault((path, qualname), (kind, line, end))
                        by_name.setdefault(qualname.rsplit(".", 1)[-1], []).append((path, qualname))
                    for scope, name, chain in script["types"]:
                        js_types.setdefault((path, scope, name), chain)
                    for qualname, chains in script["bases"].items():
                        js_bases[(path, qualname)] = chains
                    for qualname, chains in script["implements"].items():
                        js_implements[(path, qualname)] = chains
                    exports = {}
                    for name, local in script["exports"]:
                        exports.setdefault(name, local)
                    js_exports[path] = exports
                python = record.get("py")
                if not python:
                    continue
                for qualname, kind, line, end in python["defs"]:
                    defs.setdefault((path, qualname), (kind, line, end))
                    by_name.setdefault(qualname.rsplit(".", 1)[-1], []).append((path, qualname))
                for qualname, bases in python["bases"].items():
                    classes[(path, qualname)] = bases
                parts = path[:len(path) - len(os.path.splitext(path)[1])].split("/")
                if parts[-1] == "__init__":
                    parts.pop()
                for index in range(len(parts)):
                    if all(part.isidentifier() for part in parts[index:]):
                        module_names.setdefault(".".join(parts[index:]), []).append(path)
                for scope, target, chain in python["assigns"]:
                    var_types.setdefault((path, scope, target), (scope, chain))
            for paths in module_names.values():
                paths.sort(key=lambda item: (item.count("/"), item))
            attr_types = {}  # (file, class, "self.x") -> (scope, chain) from `self.x = Call()` in any method
            for (path, scope, target), value in var_types.items():
                if target.startswith("self."):
                    parts = scope.split(".")
                    owner = next((".".join(parts[:index]) for index in range(len(parts), 0, -1)
                                  if defs.get((path, ".".join(parts[:index])), ("",))[0] == "class"), None)
                    if owner:
                        attr_types.setdefault((path, owner, target), value)
            self._tables = {"defs": defs, "by_name": by_name, "modules": module_names, "classes": classes,
                            "var_types": var_types, "attr_types": attr_types, "js_types": js_types,
                            "js_bases": js_bases, "js_implements": js_implements, "js_exports": js_exports}
        return self._tables

    def user_path(self, text):
        """A file path (relative to the root or the current directory, absolute, either slash) or a module name."""
        raw = text.strip().strip("\"'")
        if not raw:
            raise CodeIndexError("empty path")
        candidates = []
        slashed = raw.replace("\\", "/")
        if os.path.isabs(raw) or _DRIVE.match(slashed) or slashed.startswith("/"):
            candidates.append(raw)
        else:
            candidates.append(os.path.join(self.root, raw.replace("\\", os.sep)))
            candidates.append(os.path.abspath(raw.replace("\\", os.sep)))
        for candidate in candidates:
            try:
                relative = os.path.relpath(os.path.abspath(candidate), self.root).replace(os.sep, "/")
            except ValueError:
                continue
            if relative == ".." or relative.startswith("../"):
                continue
            if relative in self.files:
                return relative
            folded = {path.lower(): path for path in self.files}.get(relative.lower())
            if folded:
                return folded
        if re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", raw):
            paths = self.tables()["modules"].get(raw)
            if paths:
                return paths[0]
        if not os.path.isabs(raw) and not _DRIVE.match(slashed):
            normalized = posixpath.normpath(slashed)
            for suffix in (".py", "/__init__.py") + JS_SOURCE + tuple("/index" + item for item in JS_SOURCE):
                if normalized + suffix in self.files:
                    return normalized + suffix
        raise CodeIndexError(f"not an indexed file or module under {self.root}: {text}")

    def _module_file(self, relative):
        relative = posixpath.normpath(relative) if relative else "."
        if relative == ".." or relative.startswith("../"):
            return None
        base = "" if relative == "." else relative + "/"
        for candidate in (relative + ".py", relative + ".pyi", base + "__init__.py"):
            if candidate in self.files and self.files[candidate].get("py") is not None:
                return candidate
        return None

    def resolve_module(self, path, dotted, level=0):
        """Repository file of an import in path, or None for a non-local (or ambiguous) module."""
        key = (path, dotted, level)
        if key in self._modules:
            return self._modules[key]
        here = posixpath.dirname(path)
        names = dotted.split(".") if dotted else []
        result = None
        if level:
            base = here
            for _ in range(level - 1):
                base = posixpath.dirname(base)
            result = self._module_file(posixpath.join(base, *names) if names else base)
        elif names:
            directories = [here]
            if names[0] not in STDLIB:
                ancestors, current = [], here
                while current:
                    current = posixpath.dirname(current)
                    ancestors.append(current)
                directories += ancestors + self._hints(path) + ["src"]
            for directory in directories:
                result = self._module_file(posixpath.join(directory, *names))
                if result:
                    break
            if result is None and names[0] not in STDLIB:
                paths = self.tables()["modules"].get(dotted, [])
                result = paths[0] if len(paths) == 1 else None
        self._modules[key] = result
        return result

    def _hints(self, path):
        """Directories named by string constants in this file's sys.path.insert/append calls."""
        hints, here = [], posixpath.dirname(path)
        for text in self.files[path]["py"].get("syspath", ()):
            text = text.replace("\\", "/").strip("/")
            if not re.fullmatch(r"[\w.\-]+(?:/[\w.\-]+)*", text or "-"):
                continue
            current = here
            while True:
                hints.append(posixpath.join(current, text) if current else text)
                if not current:
                    break
                current = posixpath.dirname(current)
        return hints

    def bindings(self, path):
        """Names an import binds in path: ('module', file) | ('symbol', file, name) | ('ext', dotted)."""
        if path in self._bindings:
            return self._bindings[path]
        bound = {}
        for _line, _scope, module, level, name, alias in self.files[path]["py"]["imports"]:
            if name is None:
                if alias:
                    target = self.resolve_module(path, module, level)
                    bound[alias] = ("module", target) if target else ("ext", module)
                else:
                    head = module.split(".")[0]
                    target = self.resolve_module(path, head, level)
                    full = None if target else self.resolve_module(path, module, level)
                    if full:  # A namespace package (no __init__.py): bind its directory.
                        base = full[:-len("/__init__.py")] if full.endswith("/__init__.py") else full.rsplit(".", 1)[0]
                        for _ in range(module.count(".")):
                            base = posixpath.dirname(base)
                        bound.setdefault(head, ("dir", base))
                    else:
                        bound.setdefault(head, ("module", target) if target else ("ext", head))
            elif name == "*":
                target = self.resolve_module(path, module, level)
                if target:
                    bound.setdefault("*", []).append(target)
            else:
                submodule = self.resolve_module(path, f"{module}.{name}" if module else name, level)
                if submodule:
                    bound[alias or name] = ("module", submodule)
                    continue
                target = self.resolve_module(path, module, level) if module or level else None
                bound[alias or name] = ("symbol", target, name) if target else ("ext", f"{module}.{name}".strip("."))
        self._bindings[path] = bound
        return bound

    def import_edges(self):
        """path -> [(line, scope, imported file, statement text)] for every import that resolves locally."""
        if self._edges is None:
            edges = {}
            for path, record in self.files.items():
                script = record.get("js")
                if script:
                    found = []
                    for line, scope, spec, kind, imported, local in script["imports"]:
                        target = self.js_module(path, spec)
                        if target and target != path:
                            found.append((line, scope, target, _js_label(spec, kind, imported, local)))
                    edges[path] = found
                python = record.get("py")
                if not python:
                    continue
                found = []
                for line, scope, module, level, name, alias in python["imports"]:
                    target = None
                    if name not in (None, "*"):
                        target = self.resolve_module(path, f"{module}.{name}" if module else name, level)
                    if target is None and (module or level):
                        target = self.resolve_module(path, module, level)
                    if target and target != path:
                        label = ("from " + "." * level + module + " import " + name) if name else ("import " + module)
                        found.append((line, scope, target, label + (f" as {alias}" if alias else "")))
                edges[path] = found
            self._edges = edges
        return self._edges

    # -------- JavaScript and TypeScript modules

    def _js_file(self, base, typescript):
        """The indexed file an import of base names: base itself, its TypeScript twin of a .js name, an added
        extension, or an index file."""
        files = self.files
        stem, suffix = posixpath.splitext(base)
        twins = [stem + other for other in _JS_ALTERNATES.get(suffix, ())]
        for candidate in (twins + [base]) if typescript else ([base] + twins):
            if candidate in files:
                return candidate
        prefix = base + "/" if base else ""
        suffixes = JS_SOURCE + (".d.ts",) if typescript else _JS_SOURCE_FOR_JS  # the importer's language first
        candidates = ([base + item for item in suffixes] if base else []) + [prefix + "index" + item for item in suffixes]
        for candidate in candidates:
            if candidate in files:
                return candidate
        return None

    def _config(self, path):
        """(baseUrl, paths, directory paths are relative to) of a tsconfig/jsconfig file, after local extends."""
        options = self._config_options(path)
        base = options.get("baseUrl")
        return base, options.get("paths", {}), base if base is not None else options.get("paths_dir")

    def _config_options(self, path, depth=0):
        """baseUrl and paths a config file sets or inherits: each local extends entry in order, then the file's own
        compilerOptions, override option by option (as TypeScript merges them)."""
        config = self.files[path]["tsconfig"]
        here = posixpath.dirname(path)
        options = {}
        extends = config.get("extends")
        for item in extends if isinstance(extends, list) else [extends] if extends else []:
            if isinstance(item, str) and item.startswith(".") and depth < 5:
                parent = posixpath.normpath(posixpath.join(here, item))
                parent = parent if parent.endswith(".json") else parent + ".json"
                if self.files.get(parent, {}).get("tsconfig") is not None:
                    options.update(self._config_options(parent, depth + 1))
        if config.get("baseUrl") is not None:
            base = posixpath.normpath(posixpath.join(here, config["baseUrl"]))
            options["baseUrl"] = "" if base == "." else base
        if config.get("paths"):
            options["paths"], options["paths_dir"] = config["paths"], here
        return options

    def _ts_config(self, directory):
        """Module settings of the nearest tsconfig.json or jsconfig.json at or above directory."""
        if directory not in self._configs:
            found = None
            for name in ("tsconfig.json", "jsconfig.json"):
                path = posixpath.join(directory, name) if directory else name
                if self.files.get(path, {}).get("tsconfig") is not None:
                    found = self._config(path)
                    break
            if found is None and directory:
                found = self._ts_config(posixpath.dirname(directory))
            self._configs[directory] = found
        return self._configs[directory]

    def js_module(self, path, spec):
        """Repository file of an import specifier in path, or None for a package or anything not indexed."""
        typescript = path.endswith((".ts", ".tsx", ".mts", ".cts"))
        directory = posixpath.dirname(path)
        key = (directory, spec, typescript)
        if key in self._js_modules:
            return self._js_modules[key]
        result = None
        if spec.startswith(("./", "../")) or spec in (".", ".."):
            base = posixpath.normpath(posixpath.join(directory, spec))
            if base != ".." and not base.startswith("../"):
                result = self._js_file("" if base == "." else base, typescript)
        elif spec and not spec.startswith(("/", "\\")) and ":" not in spec:
            config = self._ts_config(directory)
            if config:
                base, paths, root = config
                for pattern in sorted(paths, key=lambda item: -len(item.split("*", 1)[0])):
                    head, star, tail = pattern.partition("*")
                    if star and spec.startswith(head) and spec.endswith(tail) and len(spec) >= len(head) + len(tail):
                        middle = spec[len(head):len(spec) - len(tail)]
                    elif not star and spec == pattern:
                        middle = ""
                    else:
                        continue
                    for item in paths[pattern]:
                        candidate = posixpath.normpath(posixpath.join(root or "", item.replace("*", middle)))
                        if candidate != ".." and not candidate.startswith("../"):
                            result = self._js_file(candidate, typescript)
                            if result:
                                break
                    break
                if result is None and base is not None:
                    candidate = posixpath.normpath(posixpath.join(base, spec))
                    if candidate != ".." and not candidate.startswith("../"):
                        result = self._js_file(candidate, typescript)
        self._js_modules[key] = result
        return result

    def js_bindings(self, path):
        """Names a JS/TS file's module-level imports bind: ('symbol', file, exported name) | ('module', file) |
        ('ext', name). A require() inside a function or block binds only there (js_scoped_bindings)."""
        if path not in self._bindings:
            self._bindings[path], self._scoped[path] = {}, {}
            for _line, scope, spec, kind, imported, local in self.files[path]["js"]["imports"]:
                if not local or kind not in ("named", "default", "namespace", "require"):
                    continue
                target = self.js_module(path, spec)
                if kind == "named":
                    binding = ("symbol", target, imported) if target else ("ext", f"{spec}.{imported}")
                elif kind == "default":
                    binding = ("symbol", target, "default") if target else ("ext", spec)
                else:
                    binding = ("module", target) if target else ("ext", spec)
                if scope:
                    self._scoped[path][(scope, local)] = binding
                else:
                    self._bindings[path][local] = binding
        return self._bindings[path]

    def js_scoped_bindings(self, path):
        """(scope, name) -> binding for imports made inside a function or block (const x = require(...))."""
        self.js_bindings(path)
        return self._scoped[path]

    def js_export(self, path, name, depth=0, fallback=True):
        """What module path exports as name: a definition, a module, an external name, or None."""
        if depth > 8 or path is None or not self.files.get(path, {}).get("js"):
            return None
        tables = self.tables()
        defs = tables["defs"]
        local = tables["js_exports"].get(path, {}).get(name)
        if local is not None:
            found = self._js_local(path, local, depth + 1)
            if found:
                return found
        for _line, _scope, spec, kind, imported, alias in self.files[path]["js"]["imports"]:
            if kind in ("reexport", "reexport-namespace") and alias == name:
                target = self.js_module(path, spec)
                if kind == "reexport-namespace":
                    return ("module", target) if target else ("ext", spec)
                return self.js_export(target, imported, depth + 1) if target else ("ext", f"{spec}.{imported}")
        if name != "default":
            for _line, _scope, spec, kind, _imported, _alias in self.files[path]["js"]["imports"]:
                if kind == "reexport-all":
                    found = self.js_export(self.js_module(path, spec), name, depth + 1, False)
                    if found:
                        return found
            return None
        return ("module", path) if fallback else None  # CommonJS: the default import is the module object

    def _js_local(self, path, name, depth=0):
        """A module-level name in path: its definition, or what the import that binds it names."""
        if (path, name) in self.tables()["defs"]:
            return ("def", path, name)
        bound = self.js_bindings(path).get(name)
        return self.js_member(bound, [], depth + 1) if bound else None

    def _js_bases(self, path, qualname, depth=0):
        """Resolved base classes (or extended interfaces) of a class or interface."""
        parent = qualname.rpartition(".")[0]
        for chain in self.tables()["js_bases"].get((path, qualname), ()):
            base = self.js_resolve(path, parent, chain, depth + 1)
            if base and base[0] == "def":
                yield base

    def _js_kind(self, path, scope, chain, depth=0):
        """The class or interface a written type names, resolved from path/scope ('ext' for built-in types)."""
        if chain.startswith("!"):
            return ("ext", chain[1:])
        target = self.js_resolve(path, scope, chain, depth + 1)
        if target and target[0] == "def" and self.tables()["defs"].get((target[1], target[2]), ("",))[0] in (
                "class", "interface"):
            return target
        return None

    def _js_field(self, path, owner, name, depth=0):
        """The class or interface of this.name in class owner (or in its base classes)."""
        if depth > 8:
            return None
        chain = self.tables()["js_types"].get((path, owner, "this." + name))
        if chain:
            return self._js_kind(path, owner.rpartition(".")[0], chain, depth + 1)
        if (path, f"{owner}.{name}") in self.tables()["defs"]:  # a getter: this.name is what it returns
            return self._js_result(("def", path, f"{owner}.{name}"), depth + 1)
        for base in self._js_bases(path, owner, depth):
            found = self._js_field(base[1], base[2], name, depth + 1)
            if found:
                return found
        return None

    def _js_result(self, target, depth=0):
        """What calling a resolved target gives: an instance of a class, or the class or interface a function's
        written return type names."""
        if not target or target[0] != "def" or depth > 8:
            return ("ext", target[1] + "()") if target and target[0] == "ext" else None
        kind = self.tables()["defs"].get((target[1], target[2]), ("",))[0]
        if kind == "class":
            return target
        chain = self.tables()["js_types"].get((target[1], target[2], "()"))
        return self._js_kind(target[1], target[2], chain, depth + 1) if chain else None

    def js_member(self, target, rest, depth=0):
        """Follow member names from a resolved JS/TS target: module exports, class and namespace members,
        base classes, and instances whose class the source names (`const x = new Foo()`)."""
        if target is None or depth > 8:
            return None
        if target[0] == "ext":
            return ("ext", ".".join([target[1]] + list(rest))) if rest else target
        if target[0] == "symbol":
            resolved = self.js_export(target[1], target[2], depth + 1)
            return self.js_member(resolved, rest, depth + 1) if resolved else None
        if target[0] == "module":
            if not rest:
                return target
            found = self.js_export(target[1], rest[0], depth + 1, False)
            if found:
                return self.js_member(found, rest[1:], depth + 1)
            default = self.js_export(target[1], "default", depth + 1, False)
            return self.js_member(default, rest, depth + 1) if default and default[0] == "def" else None
        if not rest:
            return target
        path, qualname = target[1], target[2]
        defs = self.tables()["defs"]
        member = (path, f"{qualname}.{rest[0]}")
        if member in defs:
            return self.js_member(("def",) + member, rest[1:], depth + 1)
        kind = defs.get((path, qualname), ("",))[0]
        if kind in ("class", "interface"):
            for base in self._js_bases(path, qualname, depth):
                found = self.js_member(base, rest, depth + 1)
                if found:
                    return found
        elif kind == "variable":
            parent, _, name = qualname.rpartition(".")
            chain = self.tables()["js_types"].get((path, parent, name))
            instance = self._js_kind(path, parent, chain, depth + 1) if chain else None
            if instance:
                return self.js_member(instance, rest, depth + 1)
        return None

    def js_resolve(self, path, scope, chain, depth=0):
        """Resolve a JS/TS call or reference chain in path/scope like resolve() does for Python."""
        if depth > 8:
            return None
        if "()" in chain:  # a.b().c: follow written return types through each call
            segments = chain.split("()")
            target = self.js_resolve(path, scope, segments[0], depth + 1)
            for segment in segments[1:]:
                target = self._js_result(target, depth + 1)
                rest = segment.lstrip(".")
                if target and rest:
                    target = self.js_member(target, rest.split("."), depth + 1)
                if not target:
                    return None
            return target
        parts = chain.split(".")
        head, rest = parts[0], parts[1:]
        tables = self.tables()
        defs, types = tables["defs"], tables["js_types"]
        if head == "?":
            return None
        if head == "this":
            owner = self._class_of(path, scope)
            if not owner or not rest:
                return None
            if len(rest) == 1:
                return self.js_member(("def", path, owner), rest, depth + 1)
            field = self._js_field(path, owner, rest[0], depth + 1)
            return self.js_member(field, rest[1:], depth + 1) if field else None
        if head == "super":
            owner = self._class_of(path, scope)
            for base in self._js_bases(path, owner, depth) if owner else ():
                found = self.js_member(base, rest, depth + 1)
                if found:
                    return found
            return None
        current, scoped = scope, self.js_scoped_bindings(path)
        while True:
            local = scoped.get((current, head)) if scoped and current else None
            if local:  # the nearest require() binding of this name
                if not rest and local[0] == "module":
                    return self.js_export(local[1], "default", depth + 1, False)
                return self.js_member(local, rest, depth + 1)
            if defs.get((path, current), ("",))[0] not in ("class", "interface"):
                written = types.get((path, current, head))
                if written is not None and rest:
                    instance = self._js_kind(path, current, written, depth + 1)
                    return self.js_member(instance, rest, depth + 1) if instance else None
                qualname = f"{current}.{head}" if current else head
                if (path, qualname) in defs and defs[(path, qualname)][0] != "variable":
                    return self.js_member(("def", path, qualname), rest, depth + 1)
                if written is not None:
                    return None
            if not current:
                break
            current = current.rpartition(".")[0]
        bound = self.js_bindings(path).get(head)
        if bound:
            if not rest and bound[0] == "module":  # calling what require() returned: the module's default export
                return self.js_export(bound[1], "default", depth + 1, False)
            return self.js_member(bound, rest, depth + 1)
        if head in JS_GLOBALS:
            return ("ext", chain)
        return None

    # -------- name resolution

    def _class_of(self, path, scope):
        defs = self.tables()["defs"]
        parts = scope.split(".") if scope else []
        for index in range(len(parts), 0, -1):
            qualname = ".".join(parts[:index])
            if defs.get((path, qualname), ("",))[0] == "class":
                return qualname
        return None

    def _bases(self, target, depth):
        path, qualname = target[1], target[2]
        parent = qualname.rpartition(".")[0]
        for chain in self.tables()["classes"].get((path, qualname), ()):
            base = self.resolve(path, parent, chain, depth + 1)
            if base and base[0] == "def" and self.tables()["defs"].get((base[1], base[2]), ("",))[0] == "class":
                yield base

    def member(self, target, rest, depth=0):
        """Follow attribute names from a resolved target: module members, class members and base classes."""
        if target is None or depth > 8:
            return None
        defs = self.tables()["defs"]
        if not rest:
            if target[0] != "symbol":
                return target
            if (target[1], target[2]) in defs:
                return ("def", target[1], target[2])
            forwarded = self.bindings(target[1]).get(target[2])
            return self.member(forwarded, [], depth + 1) if isinstance(forwarded, tuple) else None
        if target[0] == "ext":
            return ("ext", target[1] + "." + ".".join(rest))
        if target[0] == "symbol":
            resolved = self.member(target, [], depth + 1)
            return self.member(resolved, rest, depth + 1) if resolved else None
        if target[0] == "dir":
            child = posixpath.join(target[1], rest[0])
            module = self._module_file(child)
            if module:
                return self.member(("module", module), rest[1:], depth + 1)
            if self._dirs is None:
                self._dirs = set()
                for path in self.files:
                    current = posixpath.dirname(path)
                    while current and current not in self._dirs:
                        self._dirs.add(current)
                        current = posixpath.dirname(current)
            return self.member(("dir", child), rest[1:], depth + 1) if child in self._dirs else None
        if target[0] == "module":
            path, head = target[1], rest[0]
            if (path, head) in defs:
                return self.member(("def", path, head), rest[1:], depth + 1)
            forwarded = self.bindings(path).get(head)
            if isinstance(forwarded, tuple):
                return self.member(forwarded, rest[1:], depth + 1)
            if path.endswith("__init__.py"):
                submodule = self._module_file(posixpath.join(posixpath.dirname(path), head))
                if submodule:
                    return self.member(("module", submodule), rest[1:], depth + 1)
            return None
        path, qualname = target[1], target[2]
        if (path, f"{qualname}.{rest[0]}") in defs:
            return self.member(("def", path, f"{qualname}.{rest[0]}"), rest[1:], depth + 1)
        if defs.get((path, qualname), ("",))[0] == "class":
            for base in self._bases(target, depth):
                found = self.member(base, rest, depth + 1)
                if found:
                    return found
        return None

    def resolve(self, path, scope, chain, depth=0):
        """Resolve a dotted call or reference in path/scope to ('def', file, qualname), ('module', file),
        ('ext', dotted) or None when the receiver's type is unknown."""
        if depth > 8:
            return None
        parts = chain.split(".")
        head, rest = parts[0], parts[1:]
        tables = self.tables()
        defs = tables["defs"]
        if head == "?":
            return None
        if head in ("self", "cls"):
            owner = self._class_of(path, scope)
            if not owner or not rest:
                return None
            if len(rest) > 1:
                assigned = tables["attr_types"].get((path, owner, "self." + rest[0]))
                if not assigned:
                    return None
                kind = self.resolve(path, assigned[0], assigned[1], depth + 1)
                return self.member(kind, rest[1:], depth + 1) if kind and kind[0] == "def" else None
            return self.member(("def", path, owner), rest, depth + 1)
        if head == "super()":
            owner = self._class_of(path, scope)
            for base in self._bases(("def", path, owner), depth) if owner else ():
                found = self.member(base, rest, depth + 1)
                if found:
                    return found
            return None
        scopes, current = [], scope
        while current:
            if defs.get((path, current), ("",))[0] != "class":
                scopes.append(current)
            current = current.rpartition(".")[0]
        scopes.append("")
        for where in scopes:
            qualname = f"{where}.{head}" if where else head
            if (path, qualname) in defs and defs[(path, qualname)][0] != "variable":
                return self.member(("def", path, qualname), rest, depth + 1)
            assigned = tables["var_types"].get((path, where, head))
            if assigned and rest:
                kind = self.resolve(path, assigned[0], assigned[1], depth + 1)
                if kind and kind[0] == "def" and defs.get((kind[1], kind[2]), ("",))[0] == "class":
                    return self.member(kind, rest, depth + 1)
                if kind and kind[0] == "ext":
                    return ("ext", kind[1] + "()." + ".".join(rest))
                return None
        if self.files[path].get("py") is None:
            return None
        bound = self.bindings(path).get(head)
        if isinstance(bound, tuple):
            return self.member(bound, rest, depth + 1)
        for module in self.bindings(path).get("*", []):
            if (module, head) in defs:
                return self.member(("def", module, head), rest, depth + 1)
        if (path, head) in defs:
            return self.member(("def", path, head), rest, depth + 1)
        if head in BUILTINS:
            return ("ext", chain)
        return None

    def targets(self, text):
        """Definitions a callers/affected symbol names: path::Name, module.Name, Class.method or a bare name."""
        tables = self.tables()
        defs = tables["defs"]
        text = text.strip()
        if "::" in text:
            left, _, chain = text.partition("::")
            try:
                path = self.user_path(left)
            except CodeIndexError:
                path = None
            if path:
                qualname = chain.replace("::", ".")
                if (path, qualname) in defs:
                    return {("def", path, qualname)}, path
                if self.files[path].get("py"):
                    found = self.member(("module", path), qualname.split("."))
                elif self.files[path].get("js"):
                    found = self.js_member(("module", path), qualname.split("."))
                else:
                    found = None
                return ({found} if found and found[0] == "def" else set()), path
            text = text.replace("::", ".")
        parts = text.split(".")
        for split in range(len(parts) - 1, 0, -1):
            found = set()
            for path in tables["modules"].get(".".join(parts[:split]), []):
                target = self.member(("module", path), parts[split:])
                if target and target[0] == "def":
                    found.add(target)
            if found:
                return found, None
        qualname = ".".join(parts)
        found = {("def", path, name) for path, name in tables["by_name"].get(parts[-1], ())
                 if name == qualname or name.endswith("." + qualname)}
        return found, None


def _js_label(spec, kind, imported, local):
    if kind == "named":
        return f"import {{{imported}{'' if local == imported else ' as ' + local}}} from '{spec}'"
    if kind == "default":
        return f"import {local} from '{spec}'"
    if kind == "namespace":
        return f"import * as {local} from '{spec}'"
    if kind == "require":
        return f"{local} = require('{spec}')"
    if kind == "dynamic":
        return f"import('{spec}')"
    if kind == "reexport":
        return f"export {{{imported}{'' if local == imported else ' as ' + local}}} from '{spec}'"
    if kind in ("reexport-all", "reexport-namespace"):
        return f"export *{' as ' + local if local else ''} from '{spec}'"
    return f"import '{spec}'"


# ---------------------------------------------------------------- queries


def _read_lines(index, path):
    try:
        with open(os.path.join(index.root, *path.split("/")), "rb") as handle:
            data = handle.read(MAX_FILE_BYTES + 1)
    except OSError:
        return []
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return _lines(data.decode("utf-8", errors="replace"))


def _is_test(path):
    name = path.rsplit("/", 1)[-1]
    return ("/" + path).count("/tests/") > 0 or ("/" + path).count("/test/") > 0 or name.startswith("test_") \
        or name.endswith("_test.py") or name == "conftest.py" or "/__tests__/" in "/" + path \
        or bool(_JS_TEST_NAME.search(name))


_JS_TEST_NAME = re.compile(r"\.(?:test|spec|integrationTest)\.[cm]?[jt]sx?$")


def _snippet(lines, line, limit=110):
    text = lines[line - 1].strip() if 0 < line <= len(lines) else ""
    return text if len(text) <= limit else text[:limit - 3] + "..."


def find(index, query, limit=5):
    """Rank files for a free-text description with IDF-weighted, BM25-saturated word overlap."""
    bases = query_bases(query)
    scored = [(path, record) for path, record in index.files.items() if record.get("units")]
    if not bases or not scored:
        return {"schema_version": SCHEMA_VERSION, "terms": [], "matched_files": 0, "results": []}
    wanted = {term for _, variants, _ in bases for term, _ in variants}
    path_terms = {path: _path_terms(path) for path, _ in scored}
    present, total_length, total_units = Counter(), 0.0, 0
    for path, record in scored:
        found = wanted.intersection(path_terms[path])
        for unit in record["units"]:
            total_length += unit[7]
            total_units += 1
            if len(found) < len(wanted):
                found.update(term for term in wanted if term in unit[6])
        present.update(found)
    count = len(scored)
    idf = {term: math.log(1 + (count - present[term] + 0.5) / (present[term] + 0.5)) for term in present}
    bases = [base for base in bases if any(term in idf for term, _ in base[1])]
    if not bases:
        return {"schema_version": SCHEMA_VERSION, "terms": [], "matched_files": 0, "results": []}
    base_idf = [max(idf.get(term, 0.0) * weight for term, weight in variants) for _, variants, _ in bases]
    coverage_total = sum(value for value, base in zip(base_idf, bases) if base[2]) or 1.0
    average_unit = total_length / max(total_units, 1)
    file_lengths = {path: sum(unit[7] for unit in record["units"]) for path, record in scored}
    average_file = sum(file_lengths.values()) / max(len(file_lengths), 1)
    query_words = {_stem(word) for word in re.findall(r"[A-Za-z]+", query.lower())}
    wants_tests, wants_docs = bool(query_words & {_stem(w) for w in TEST_WORDS}), bool(
        query_words & {_stem(w) for w in DOC_WORDS})

    def score(get, length, average):
        norm = K1 * (1 - B + B * length / max(average, 1e-9))
        total, covered = 0.0, 0.0
        for (_, variants, counts), weight in zip(bases, base_idf):
            best, primary = 0.0, False
            for position, (term, factor) in enumerate(variants):
                value = get(term)
                if value and term in idf:
                    gain = factor * idf[term] * value * (K1 + 1) / (value + norm)
                    if gain > best:
                        best, primary = gain, position == 0
            if best:
                total += best
                if counts:
                    covered += weight if primary else weight * SYNONYM_WEIGHT
        share = covered / coverage_total
        return total * (0.25 + 0.75 * share) ** 2

    ranked = []
    for path, record in scored:
        path_words = path_terms[path]
        if not wanted.intersection(path_words) and not any(
                term in unit[6] for unit in record["units"] for term in wanted):
            continue
        best, best_unit, whole = 0.0, None, {}
        for term, value in path_words.items():
            if term in wanted:
                whole[term] = value
        for unit in record["units"]:
            terms = unit[6]
            if not any(term in terms for term in wanted) and not any(term in path_words for term in wanted):
                continue
            for term in wanted:
                if term in terms:
                    whole[term] = whole.get(term, 0.0) + terms[term]
            value = score(lambda term, terms=terms: terms.get(term, 0.0) + path_words.get(term, 0.0),
                          unit[7], average_unit)
            if value > best or best_unit is None:
                best, best_unit = value, unit
        total = best + FILE_WEIGHT * score(whole.get, file_lengths[path], average_file)
        if record["kind"] not in CODE_KINDS and record["kind"] in ("markdown", "text") and not wants_docs:
            total *= DOC_FACTOR
        if _is_test(path) and not wants_tests:
            total *= TEST_FACTOR
        ranked.append((total, path, best_unit))
    ranked.sort(key=lambda item: (-item[0], item[1].count("/"), item[1]))
    results, by_digest = [], {}
    for total, path, unit in ranked:
        digest = index.files[path].get("sha256")
        if digest and digest in by_digest:
            by_digest[digest].setdefault("duplicates", []).append(path)
            continue
        if len(results) >= limit:
            continue
        result = {"path": path, "score": round(total, 2), "symbol": "", "line": unit[2] if unit else 1}
        result["_unit"] = unit
        results.append(result)
        if digest:
            by_digest[digest] = result
    for result in results:
        _place(index, result, bases, idf)
    return {"schema_version": SCHEMA_VERSION, "terms": [base[0] for base in bases], "matched_files": len(ranked),
            "results": results}


def _place(index, result, bases, idf):
    """Pick the best line inside the best unit, then name the innermost definition that holds it."""
    unit = result.pop("_unit")
    record = index.files[result["path"]]
    lines = _read_lines(index, result["path"])
    result["_lines"] = lines
    if not unit:
        return
    best_line, best = unit[2], -1.0
    for number in range(unit[3], min(unit[4], len(lines)) + 1):
        present = set(words(lines[number - 1]))
        if not present:
            continue
        value = sum(max((factor * idf.get(term, 0.0) for term, factor in variants if term in present), default=0.0)
                    for _, variants, _ in bases)
        if number == unit[2]:
            value *= 1.25
        if value > best:
            best_line, best = number, value
    result["line"] = best_line
    holders = [item for item in record["units"] if item[0] and item[3] <= best_line <= item[4]]
    if holders:
        holder = max(holders, key=lambda item: (item[3], -item[4]))
        result["symbol"] = holder[0]
        if len(holder) > 8 and best_line <= holder[8]:
            result["line"] = holder[2]
    elif unit[0]:
        result["symbol"] = unit[0]


def _scope_label(scope):
    return _plain_scope(scope) or "<module>"


LIMITS = ("complete means every match in this index, not every real caller: only Python and JavaScript/"
          "TypeScript calls and imports are indexed; dynamic dispatch, string-named calls, reflection, dependency "
          "injection and values of unknown type are not followed, and in Python a method called on what an "
          "external call returned (x = frappe.get_doc(...); x.save()) counts as external, not as a caller")


def _is_js(index, path):
    return index.files.get(path, {}).get("js") is not None


def _completeness(total, shown):
    return {"complete": total <= shown, "truncated": max(0, total - shown), "limits": LIMITS}


def _js_dispatch(index, targets):
    """Methods a call may reach a JS/TS target method through: the same name on its class's ancestors and on
    the interfaces they implement (a call resolved to one of these may run the target at run time)."""
    found = set()
    tables = index.tables()
    defs = tables["defs"]
    for target in targets:
        if not _is_js(index, target[1]) or "." not in target[2]:
            continue
        owner, _, name = target[2].rpartition(".")
        if defs.get((target[1], owner), ("",))[0] != "class":
            continue
        seen, queue = set(), deque([("def", target[1], owner)])
        while queue and len(seen) < 64:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            if current[0] != "def":
                continue
            parent = current[2].rpartition(".")[0]
            for chain in tables["js_implements"].get((current[1], current[2]), ()):
                kind = index._js_kind(current[1], parent, chain)
                if kind:
                    queue.append(kind)
            queue.extend(index._js_bases(current[1], current[2]))
        for kind in seen - {("def", target[1], owner)}:
            if kind[0] == "def" and (kind[1], f"{kind[2]}.{name}") in defs:
                found.add(("def", kind[1], f"{kind[2]}.{name}"))
    return found


def _js_abstract(index, target):
    """Whether a resolved JS/TS target is an interface member (the receiver's concrete class is not known)."""
    if target[0] != "def":
        return False
    defs = index.tables()["defs"]
    return defs.get((target[1], target[2].rpartition(".")[0]), ("",))[0] == "interface"


def callers(index, symbol, limit=50):
    """Call sites of the named definition(s). Calls on receivers of unknown type that use the same name come
    after the resolved ones, those whose receiver is named like the target's class first (for JS/TS also
    calls that resolve to the same method on a base class or an implemented interface)."""
    targets, path = index.targets(symbol)
    names = {target[2].rsplit(".", 1)[-1] for target in targets}
    classes = {target for target in targets
               if index.tables()["defs"].get((target[1], target[2]), ("",))[0] == "class"}
    wanted = set(targets)
    for target in list(targets):  # Instantiating a class calls its __init__ (its constructor in JS/TS).
        if target[2].endswith(".__init__") or (target[2].endswith(".constructor") and _is_js(index, target[1])):
            wanted.add(("def", target[1], target[2].rsplit(".", 1)[0]))
            names.add(target[2].rsplit(".", 2)[-2])
    owners = set()  # Receiver names that suggest the target's class: index.resolve() for Index.resolve.
    for target in targets:
        if "." in target[2]:
            owner = target[2].rsplit(".", 2)[-2]
            parts = _CAMEL.findall(owner)
            owners.update({owner.lower(), "_".join(parts).lower(), parts[-1].lower() if parts else ""} - {""})
    dispatch = _js_dispatch(index, targets)
    reach = _js_reach(index, targets)
    external = None
    if not targets and path is None:
        external = symbol.strip().replace("::", ".")
        names = {external.rsplit(".", 1)[-1]}
    rows = []
    for file, record in sorted(index.files.items()):
        python, script = record.get("py"), record.get("js")
        if python:
            local, calls, resolve = names | _aliases(index, file, names), python["calls"], index.resolve
        elif script:
            local = names | _js_aliases(index, file, names, reach, targets)
            calls, resolve = script["calls"], index.js_resolve
        else:
            continue
        for line, scope, chain in calls:
            last = chain.rsplit(".", 1)[-1]
            if last not in local:
                continue
            target = resolve(file, scope, chain)
            if external is not None:
                if target and target[0] == "ext" and (target[1] == external or target[1].endswith("." + external)
                                                      or chain == external):
                    rows.append((0, file, line, scope))
                continue
            if target and (target in wanted or target in classes):
                rows.append((0, file, line, scope))
            elif target is None or target in dispatch or (script and _js_abstract(index, target)):
                # Receiver type unknown (or a name nothing defines, or only an interface is known).
                receiver = chain.rsplit(".", 2)[-2].strip("_#").lower() if "." in chain else ""
                rows.append((1 if receiver in owners or target in dispatch else 2, file, line, scope))
    rows.sort()
    results = [{"path": file, "line": line, "symbol": _scope_label(scope), "resolved": rank == 0}
               for rank, file, line, scope in rows[:limit]]
    report = {"schema_version": SCHEMA_VERSION, "targets": [f"{t[1]}::{t[2]}" for t in sorted(targets)]
              or ([external] if external else []), "total": len(rows),
              "resolved": sum(1 for row in rows if not row[0]), "results": results}
    report.update(_completeness(len(rows), len(results)))
    return report


def import_path(index, source, target):
    """Shortest import chain from source to target; if there is none, from target back to source."""
    start, goal = index.user_path(source), index.user_path(target)
    for module in (start, goal):
        if index.files[module].get("py") is None and index.files[module].get("js") is None:
            raise CodeIndexError(f"not a Python or JavaScript/TypeScript module: {module}")
    edges = index.import_edges()
    for first, last, direction in ((start, goal, "forward"), (goal, start, "reverse")):
        previous, queue = {first: None}, deque([first])
        while queue:
            current = queue.popleft()
            if current == last:
                chain = []
                while current is not None:
                    chain.append(current)
                    current = previous[current]
                return {"schema_version": SCHEMA_VERSION, "path": chain[::-1], "direction": direction}
            for _, _, imported, _ in sorted(edges.get(current, ()), key=lambda edge: edge[2]):
                if imported not in previous:
                    previous[imported] = current
                    queue.append(imported)
    return {"schema_version": SCHEMA_VERSION, "path": [], "direction": None}


def affected(index, target, hops=1, limit=50):
    """Files that import the module, or call/import/reference the symbol; hops=2 adds their dependants."""
    left, separator, chain = target.strip().partition("::")
    path = index.user_path(left)
    edges = index.import_edges()
    importers = {}
    for file, found in edges.items():
        for line, scope, imported, label in found:
            if imported == path:
                importers.setdefault(file, []).append((line, scope, label))
    rows, seen = [], {path}

    def add(file, line, scope, label, hop):
        if file not in seen:
            seen.add(file)
            rows.append({"path": file, "line": line, "symbol": _scope_label(scope), "hop": hop, "_label": label})

    if index.files[path].get("py") is None and index.files[path].get("js") is None:
        report = {"schema_version": SCHEMA_VERSION, "target": path, "total": 0, "results": [],
                  "note": "only Python and JavaScript/TypeScript imports and calls are tracked"}
        report.update(_completeness(0, 0))
        return report
    if not separator:
        for file in sorted(importers):
            line, scope, label = min(importers[file])
            add(file, line, scope, label, 1)
        if hops > 1:
            for row in list(rows):
                for file, found in sorted(edges.items()):
                    for line, scope, imported, label in sorted(found):
                        if imported == row["path"]:
                            add(file, line, scope, label + f" (via {row['path']})", 2)
    else:
        qualname = chain.replace("::", ".")
        defs = index.tables()["defs"]
        if (path, qualname) not in defs:
            report = {"schema_version": SCHEMA_VERSION, "target": f"{path}::{qualname}", "total": 0,
                      "note": "no such definition", "results": []}
            report.update(_completeness(0, 0))
            return report
        sites = _symbol_sites(index, ("def", path, qualname))
        hop_scopes = []
        for file, line, scope, label in sites:
            hop_scopes.append((file, scope))
            if file == path and scope.split(".")[0] == qualname.split(".")[0]:
                continue
            if file == path:
                seen.discard(path)
            add(file, line, scope, label, 1)
        if hops > 1:
            for file, scope in hop_scopes:
                scope = _owner_scope(scope)
                if scope and (file, scope) in defs:
                    for other, line, where, label in _symbol_sites(index, ("def", file, scope)):
                        add(other, line, where, label + f" (via {file}::{_plain_scope(scope)})", 2)
                else:
                    for other, found in sorted(edges.items()):
                        for line, where, imported, label in sorted(found):
                            if imported == file:
                                add(other, line, where, label + f" (via {file})", 2)
    rows.sort(key=lambda row: (row["hop"], row["path"]))
    report = {"schema_version": SCHEMA_VERSION, "target": path + (f"::{chain.replace('::', '.')}" if separator else ""),
              "total": len(rows), "results": rows[:limit], "hops": hops}
    report.update(_completeness(len(rows), len(report["results"])))
    return report


def _aliases(index, path, names):
    """Local names that `from module import name as alias` binds to one of names."""
    return {alias for alias, bound in index.bindings(path).items()
            if isinstance(bound, tuple) and bound[0] == "symbol" and bound[2] in names}


def _js_reach(index, targets):
    """Names under which JS/TS modules export one of targets beyond its own name: export-list and re-export
    aliases (export {original as renamed} [from ...]) and default exports, followed through re-export chains."""
    targets = {target for target in targets if _is_js(index, target[1])}
    names = {target[2] for target in targets}
    found = set()
    for path, table in index.tables()["js_exports"].items():
        for exported, local in table.items():
            if exported != local and local in names and index.js_export(path, exported, 0, False) in targets:
                found.add(exported)
    for _ in range(5):
        grown = False
        for path, record in index.files.items():
            for _line, _scope, _spec, kind, imported, alias in (record.get("js") or {}).get("imports", ()):
                if kind == "reexport" and alias not in found and alias not in names and imported in names | found \
                        and index.js_export(path, alias, 0, False) in targets:
                    found.add(alias)
                    grown = True
        if not grown:
            break
    return found


def _js_aliases(index, path, names, reach=(), targets=()):
    """Local names that bind one of names: `import {name as alias}`, a default import, and (with reach and
    targets from _js_reach) imports of re-export aliases, plus alias names reached through a namespace import."""
    found = set()
    for _line, _scope, spec, kind, imported, local in index.files[path]["js"]["imports"]:
        if not local or local in names:
            continue
        if kind == "named" and imported in names:
            found.add(local)
        elif kind == "named" and imported in reach:
            module = index.js_module(path, spec)
            if module and index.js_export(module, imported, 0, False) in targets:
                found.add(local)
        elif kind == "default":
            module = index.js_module(path, spec)
            exported = index.tables()["js_exports"].get(module, {}).get("default") if module else None
            if (exported and exported.rsplit(".", 1)[-1] in names) or (
                    targets and module and index.js_export(module, "default", 0, False) in targets):
                found.add(local)  # also `export { original as default } from ...` in a barrel
        elif kind in ("namespace", "require"):
            module = index.js_module(path, spec)
            if module and kind == "require" and targets and index.js_export(module, "default", 0, False) in targets:
                found.add(local)  # const renamed = require('./lib'); renamed()
            if module and reach:
                found.update(alias for alias in reach if index.js_export(module, alias, 0, False) in targets)
    return found


def _symbol_sites(index, target):
    """(file, line, scope, label) where a definition is called, imported by name, or referenced as module.name."""
    defs = index.tables()["defs"]
    name = target[2].rsplit(".", 1)[-1]
    script = _is_js(index, target[1])
    unique = sum(1 for path, _ in index.tables()["by_name"].get(name, ()) if _is_js(index, path) == script) == 1
    is_class = defs.get((target[1], target[2]), ("",))[0] == "class"
    sites, reach = [], (_js_reach(index, {target}) if script else set())
    for file, record in sorted(index.files.items()):
        if script:
            if record.get("js"):
                sites.extend(_js_sites(index, target, file, record["js"], name, unique, is_class, reach))
            continue
        python = record.get("py")
        if not python:
            continue
        local = {name} | _aliases(index, file, {name})
        for line, scope, chain in python["calls"]:
            if chain.rsplit(".", 1)[-1] not in local:
                continue
            resolved = index.resolve(file, scope, chain)
            if resolved == target or (resolved is None and unique and "." in chain and not is_class):
                sites.append((file, line, scope, f"calls {chain}"))
        for line, scope, module, level, imported, alias in python["imports"]:
            if imported == name:
                bound = index.bindings(file).get(alias or imported)
                if isinstance(bound, tuple) and bound[0] == "symbol" and index.member(bound, []) == target:
                    sites.append((file, line, scope, f"imports {name}"))
        for line, scope, chain in python["refs"]:
            if chain.rsplit(".", 1)[-1] == name and index.resolve(file, scope, chain) == target:
                sites.append((file, line, scope, f"uses {chain}"))
    return sorted(set(sites), key=lambda site: (site[0], site[1]))


def _js_sites(index, target, file, script, name, unique, is_class, reach=()):
    local = {name} | _js_aliases(index, file, {name}, reach, {target})
    for line, scope, chain in script["calls"]:
        if chain.rsplit(".", 1)[-1] not in local:
            continue
        resolved = index.js_resolve(file, scope, chain)
        if resolved == target or (resolved is None and unique and "." in chain and not is_class):
            yield file, line, scope, f"calls {chain}"
    for line, scope, spec, kind, imported, alias in script["imports"]:
        if (kind in ("named", "reexport") and (imported == name or imported in reach)) or (
                kind == "default" and alias in local):
            module = index.js_module(file, spec)
            if module and index.js_export(module, imported, 0, False) == target:
                yield file, line, scope, f"imports {alias}"
    for line, scope, chain in script["refs"]:
        if chain.rsplit(".", 1)[-1] == name and index.js_resolve(file, scope, chain) == target:
            yield file, line, scope, f"uses {chain}"


OVERVIEW_CHARS = 6000  # about 1.5k tokens
_OVERVIEW_LIMITS = ("pointers only; most-called = PageRank over call sites this index resolves (Python and "
                    "JavaScript/TypeScript, tests excluded); unresolved calls are not counted")


def call_graph(index):
    """Counter of resolved call edges (caller (path, scope), callee (path, qualname)), test files left out."""
    by_name, edges = index.tables()["by_name"], Counter()
    for path, record in index.files.items():
        python, script = record.get("py"), record.get("js")
        if _is_test(path) or not (python or script):
            continue
        resolve, seen = (index.resolve if python else index.js_resolve), {}
        bound = index.bindings(path) if python else set(index.js_bindings(path)) | {  # import aliases (a as b)
            name for _scope, name in index.js_scoped_bindings(path)}
        for _line, scope, chain in (python or script)["calls"]:
            if chain.rsplit(".", 1)[-1] not in by_name and chain.split(".", 1)[0] not in bound:
                continue
            key = (scope, chain)
            if key not in seen:
                seen[key] = resolve(path, scope, chain)
            target = seen[key]
            if target and target[0] == "def" and not _is_test(target[1]):
                edges[((path, _owner_scope(scope)), (target[1], target[2]))] += 1
    return edges


def pagerank(edges, damping=0.85, rounds=60, tolerance=1e-9):
    """PageRank of a weighted directed graph {(source, target): weight}, by power iteration."""
    nodes = sorted({node for edge in edges for node in edge})
    if not nodes:
        return {}
    number = {node: index for index, node in enumerate(nodes)}
    out = [0.0] * len(nodes)
    links = []
    for (source, target), weight in edges.items():
        out[number[source]] += weight
        links.append((number[source], number[target], weight))
    size = len(nodes)
    rank = [1.0 / size] * size
    for _ in range(rounds):
        dangling = sum(rank[index] for index in range(size) if not out[index])
        fresh = [(1.0 - damping + damping * dangling) / size] * size
        for source, target, weight in links:
            fresh[target] += damping * rank[source] * weight / out[source]
        change = sum(abs(a - b) for a, b in zip(fresh, rank))
        rank = fresh
        if change < tolerance:
            break
    return {node: rank[number[node]] for node in nodes}


def overview(index, max_chars=OVERVIEW_CHARS):
    """One page of pointers: entry points, main directories and modules, and the most-called definitions."""
    defs = index.tables()["defs"]
    entries, by_dir, modules = [], {}, []
    for path, record in sorted(index.files.items()):
        python, script, package = record.get("py"), record.get("js"), record.get("package")
        if package and not _is_test(path):
            directory = posixpath.dirname(path)
            keys = package.get("lines", {})
            targets = [(key, package[key]) for key in ("main", "module") if package.get(key)]
            bins = package.get("bin")
            targets += [("bin", bins)] if isinstance(bins, str) else [("bin " + name, value)
                                                                         for name, value in sorted((bins or {}).items())]
            for key, value in targets:
                found = index._js_file(posixpath.normpath(posixpath.join(directory, value)), True)
                entries.append({"path": path, "line": keys.get(key.split()[0], 1), "kind": "package.json " + key,
                                "target": found or value, "indexed": bool(found)})
        if python and not _is_test(path):
            parser_line = min((line for line, _scope, chain in python["calls"]
                               if chain.rsplit(".", 1)[-1] == "ArgumentParser"), default=None)
            kinds = (["__main__.py"] if path.rsplit("/", 1)[-1] == "__main__.py" else []) + (
                ['if __name__ == "__main__"'] if python.get("main") else []) + (["argparse"] if parser_line else [])
            if kinds:
                entries.append({"path": path, "line": python.get("main") or parser_line or 1, "kind": ", ".join(kinds)})
        if script and script.get("main") and not _is_test(path):
            entries.append({"path": path, "line": 1, "kind": "#! node script"})
        if record.get("kind") not in CODE_KINDS:
            continue
        count = len((python or script or {}).get("defs", ()))
        modules.append((count, path))
        parts = path.split("/")[:-1]
        for depth in range(len(parts) + 1):
            totals = by_dir.setdefault("/".join(parts[:depth]), [0, 0])
            totals[0] += 1
            totals[1] += count
    entries.sort(key=lambda entry: (entry["path"].count("/"), entry["kind"] != "package.json main", entry["path"]))

    def children(directory):
        prefix = directory + "/" if directory else ""
        found = [(key, value) for key, value in by_dir.items()
                 if key.startswith(prefix) and key != directory and "/" not in key[len(prefix):]]
        return sorted(found, key=lambda item: (-item[1][1], -item[1][0], item[0]))

    top = children("")
    inside, current = None, ""
    while by_dir.get(current, [0, 0])[1]:
        below = children(current)
        if not below or below[0][1][1] < 0.7 * by_dir[current][1]:
            break
        current = below[0][0]
    if current:
        inside = current
    edges = call_graph(index)
    ranks = pagerank(edges)
    calls_in = Counter()
    for (_source, target), weight in edges.items():
        calls_in[target] += weight
    ranked = sorted((node for node in ranks if node[1] and node in defs),
                    key=lambda node: (-ranks[node], node))
    report = {"schema_version": SCHEMA_VERSION, "files": len(index.files),
              "definitions": len(defs), "resolved_call_edges": sum(edges.values()),
              "entry_points": [], "directories": [], "inside": inside, "inside_directories": [], "modules": [],
              "most_called": [], "limits": _OVERVIEW_LIMITS}
    lines, cut, owners = [], {}, []
    budget = max_chars - 120  # room for the closing "truncated: ..." line

    def emit(text, section=None, row=None):
        size = sum(len(line) + 1 for line in lines)
        if size + len(text) + 1 > budget:
            if section:
                cut[section] = cut.get(section, 0) + 1
            return False
        lines.append(text)
        owners.append(section)
        if section:
            report[section].append(row)
        return True

    kinds = Counter(record.get("kind", "?") for record in index.files.values())
    emit(f"{len(index.files)} files ({', '.join(f'{kind} {count}' for kind, count in sorted(kinds.items()))}); "
         f"{len(defs)} definitions; {sum(edges.values())} resolved call sites")
    emit("Entry points:")
    for entry in entries[:25]:
        detail = f"  {entry['path']}:{entry['line']}  {entry['kind']}"
        if "target" in entry:
            detail += f" -> {entry['target']}" + ("" if entry["indexed"] else " (not in the index)")
        emit(detail, "entry_points", entry)
    if len(entries) > 25:
        cut["entry_points"] = cut.get("entry_points", 0) + len(entries) - 25
    if not entries:
        emit("  (none found)")
    emit("Top-level directories (code files, definitions):")
    for key, (files, count) in top[:12]:
        emit(f"  {key}/  {files} files  {count} defs", "directories", {"path": key, "files": files, "definitions": count})
    if len(top) > 12:
        cut["directories"] = len(top) - 12
    if inside:
        emit(f"Inside {inside}/ (code files, definitions):")
        for key, (files, count) in children(inside)[:12]:
            emit(f"  {key}/  {files} files  {count} defs", "inside_directories",
                 {"path": key, "files": files, "definitions": count})
    emit("Largest modules (definitions):")
    for count, path in sorted(modules, key=lambda item: (-item[0], item[1]))[:8]:
        emit(f"  {path}  {count} defs", "modules", {"path": path, "definitions": count})
    emit("Most-called definitions, top 20 (PageRank over resolved call sites, tests excluded):")
    sources = {}
    for node in ranked[:20]:
        kind, line, _end = defs[node]
        if node[0] not in sources:
            sources[node[0]] = _read_lines(index, node[0])
        signature = _snippet(sources[node[0]], line, 100)
        row = {"path": node[0], "line": line, "symbol": node[1], "kind": kind, "calls": calls_in[node],
               "signature": signature}
        if not emit(f"  {node[0]}:{line}  {node[1]}  [{kind}, {calls_in[node]} calls]\n      {signature}",
                    "most_called", row):
            break
    while True:
        closing = ["truncated: " + ", ".join(f"{key} {value} more" for key, value in sorted(cut.items()))] if cut \
            else []
        if len("\n".join(lines + closing)) <= max_chars or not lines:
            break
        section = owners.pop()  # drop rows from the end until the page fits
        lines.pop()
        if section:
            report[section].pop()
            cut[section] = cut.get(section, 0) + 1
    report["truncated"] = dict(sorted(cut.items()))
    lines += closing
    report["text"] = "\n".join(lines)
    report["chars"] = len(report["text"])
    return report


def stats(index):
    kinds = Counter(record.get("kind", "?") for record in index.files.values())
    symbols = imports = calls = 0
    for record in index.files.values():
        python = record.get("py") or record.get("js")
        if python:
            symbols += len(python["defs"])
            imports += len(python["imports"])
            calls += len(python["calls"])
        else:
            symbols += sum(1 for unit in record.get("units", ()) if unit[0])
    info = index.info
    cache = None
    if info["cache"]:
        try:
            size = os.path.getsize(info["cache"]) + os.path.getsize(_units_file(info["cache"]))
        except OSError:
            size = None
        cache = {"path": info["cache"], "origin": info.get("cache_origin", "--cache"), "bytes": size,
                 "reused": info["counts"].get("reused", 0),
                 "indexed": info["counts"].get("indexed", 0), "removed": info["removed"],
                 "stale": info["stale"], "frozen": info["frozen"]}
    skipped = {key: value for key, value in info["counts"].items()
               if key in ("binary", "generated copies", "links", "skipped directories", "unreadable")}
    return {"schema_version": SCHEMA_VERSION, "root": index.root, "files": len(index.files), "kinds": dict(kinds),
            "symbols": symbols, "imports": imports, "calls": calls, "skipped": skipped,
            "parse_fallbacks": sorted(path for path, record in index.files.items() if record.get("error")),
            "build_seconds": round(info["seconds"], 3), "cache": cache}


# ---------------------------------------------------------------- command line


def _print_find(index, report):
    results = report["results"]
    if not results:
        print("No matching files." if report["terms"] else "No searchable words in the query.")
        return
    print(f"{len(results)} of {report['matched_files']} matching files; words: {' '.join(report['terms'])}")
    for result in results:
        symbol = f"  {result['symbol']}" if result["symbol"] else ""
        print(f"{result['path']}:{result['line']}{symbol}  [{result['score']}]")
        snippet = _snippet(result.get("_lines", []), result["line"])
        if snippet:
            print(f"    {snippet}")
        if result.get("duplicates"):
            print(f"    same content: {', '.join(result['duplicates'][:3])}"
                  + (f" (+{len(result['duplicates']) - 3})" if len(result["duplicates"]) > 3 else ""))


def _print_sites(index, report, verb):
    rows = report["results"]
    cache = {}
    for row in rows:
        if row["path"] not in cache:
            cache[row["path"]] = _read_lines(index, row["path"])
        mark = "" if row.get("resolved", True) else "~ "
        hop = f"[hop {row['hop']}] " if row.get("hop", 1) > 1 else ""
        print(f"{mark}{hop}{row['path']}:{row['line']}  {row['symbol']}  {_snippet(cache[row['path']], row['line'], 90)}")
    if verb == "callers" and any(not row.get("resolved", True) for row in rows):
        print("~ = same name on a receiver whose type is not known; check before relying on it")
    print(_completeness_line(report))


def _completeness_line(report):
    scope = "Python and JS/TS calls and imports"
    if "hops" in report:
        scope += f", {report['hops']} hop" + ("s" if report["hops"] > 1 else "")
    if report.get("truncated"):
        return f"truncated: {report['truncated']} more (raise --limit); within the index ({scope})"
    return f"complete within the index ({scope}; dynamic dispatch, string-named calls, reflection and DI not followed)"


def _emit(report, as_json, printer):
    if as_json:
        clean = dict(report)
        clean["results"] = [{key: value for key, value in row.items() if not key.startswith("_")}
                            for row in report.get("results", ())]
        print(json.dumps(clean, ensure_ascii=False, indent=1))
    else:
        printer()


def parser():
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--root", default=argparse.SUPPRESS, help="repository root to index (default: current directory)")
    shared.add_argument("--cache", metavar="DIR", default=argparse.SUPPRESS,
                        help=f"keep the index in DIR and refresh stale files (default: ${CACHE_ENV}, else the "
                             "user cache directory, ~/.cache/oaw/code-index or %%LOCALAPPDATA%%\\oaw\\code-index)")
    shared.add_argument("--no-cache", action="store_true", default=argparse.SUPPRESS,
                        help="index on the fly and write nothing")
    shared.add_argument("--frozen", action="store_true", default=argparse.SUPPRESS,
                        help="use the cache as it is and report stale files instead of re-indexing them")
    shared.add_argument("--include-generated", action="store_true", default=argparse.SUPPRESS,
                        help="also index example copies that sync_examples.py marked as generated")
    shared.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="print JSON (schema_version 1)")
    result = argparse.ArgumentParser(
        prog="code_index.py", parents=[shared], formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Read-only code index for locating code: ranked files, call sites, import chains.",
        epilog="""
Commands:
  find "free text" [--limit 5]        Rank files and the best symbol/line for a description
  callers SYMBOL [--limit N]          Call sites of path::Name, module.func, Class.method or a name
  path A B                            Shortest import chain between two local modules
  affected PATH[::Symbol] [--hops 2]  Files that import the module or call the symbol
  overview                            One page: entry points, main directories, most-called code
  stats                               Files, symbols, build time and cache state

Python is parsed with ast; JavaScript and TypeScript with a scanner that
resolves imports (relative, index files, tsconfig paths), this/super, class
bases and written types. The index is cached in the user's local cache
directory (not in the project, not on a network share by default) and
re-indexed where a file's size or content changed; --no-cache indexes on the
fly. Results are pointers to read in the source, not descriptions of behavior;
callers and affected say whether a list is complete within the index.
""")
    commands = result.add_subparsers(dest="command", required=True, metavar="COMMAND")
    find_parser = commands.add_parser("find", parents=[shared], help="rank files for a free-text description")
    find_parser.add_argument("query", nargs="+", help="what the code does, in words or identifiers")
    find_parser.add_argument("--limit", type=_limit, default=5, help="results to show (default 5)")
    callers_parser = commands.add_parser("callers", parents=[shared], help="call sites of a function, method or class")
    callers_parser.add_argument("symbol", help="path::Name, module.func, Class.method or a bare name")
    callers_parser.add_argument("--limit", type=_limit, default=50, help="call sites to show (default 50)")
    path_parser = commands.add_parser("path", parents=[shared], help="shortest import chain between two local modules")
    path_parser.add_argument("source", help="file path or dotted module name")
    path_parser.add_argument("target", help="file path or dotted module name")
    affected_parser = commands.add_parser("affected", parents=[shared],
                                          help="files that import a module or call a symbol")
    affected_parser.add_argument("target", help="PATH or PATH::Symbol (Class.method or Class::method)")
    affected_parser.add_argument("--hops", type=int, choices=(1, 2), default=1, help="1 (default) or 2")
    affected_parser.add_argument("--limit", type=_limit, default=50, help="files to show (default 50)")
    commands.add_parser("overview", parents=[shared],
                        help="one page: entry points, main directories, most-called definitions")
    commands.add_parser("stats", parents=[shared], help="files, symbols, build time and cache state")
    return result


def _limit(value):
    try:
        number = int(value)
    except ValueError:
        number = 0
    if not 1 <= number <= 1000:
        raise argparse.ArgumentTypeError("must be an integer from 1 to 1000")
    return number


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    command_line = parser()
    args = command_line.parse_args(argv)
    as_json = getattr(args, "json", False)
    if getattr(args, "no_cache", False) and getattr(args, "cache", None):
        command_line.error("--cache and --no-cache cannot be combined")
    try:
        root = getattr(args, "root", ".")
        cache, origin = choose_cache(root, getattr(args, "cache", None), getattr(args, "no_cache", False))
        index = build_index(root, cache, getattr(args, "frozen", False), getattr(args, "include_generated", False),
                            need_units=args.command == "find")
        index.info["cache_origin"] = origin
        if index.info["stale"]:
            names = index.info["stale"]
            print(f"code_index: {len(names)} stale file(s) not re-indexed (--frozen): "
                  + ", ".join(names[:5]) + (" ..." if len(names) > 5 else ""), file=sys.stderr)
        if args.command == "find":
            report = find(index, " ".join(args.query), args.limit)
            _emit(report, as_json, lambda: _print_find(index, report))
        elif args.command == "callers":
            report = callers(index, args.symbol, args.limit)

            def show():
                if not report["results"]:
                    print(f"No call sites of {', '.join(report['targets']) or args.symbol}.")
                    print(_completeness_line(report))
                    return
                resolved = report["resolved"]
                print(f"{report['total']} call sites of {', '.join(report['targets'][:3])}"
                      + (f" (+{len(report['targets']) - 3} more definitions)" if len(report["targets"]) > 3 else "")
                      + f"; {resolved} resolved")
                _print_sites(index, report, "callers")
            _emit(report, as_json, show)
        elif args.command == "path":
            report = import_path(index, args.source, args.target)

            def show():
                if not report["path"]:
                    print(f"No import chain between {args.source} and {args.target}.")
                else:
                    note = "" if report["direction"] == "forward" else "  (reverse: the second imports the first)"
                    print(" -> ".join(report["path"]) + note)
            _emit(report, as_json, show)
        elif args.command == "affected":
            report = affected(index, args.target, args.hops, args.limit)

            def show():
                if not report["results"]:
                    print(f"Nothing else imports or calls {report['target']}."
                          + (f" ({report['note']})" if report.get("note") else ""))
                    print(_completeness_line(report))
                    return
                print(f"{report['total']} files affected by {report['target']} ({args.hops} hop"
                      + ("s" if args.hops > 1 else "") + ")")
                _print_sites(index, report, "affected")
            _emit(report, as_json, show)
        elif args.command == "overview":
            report = overview(index)
            if as_json:
                print(json.dumps({key: value for key, value in report.items() if key != "text"}, ensure_ascii=False,
                                 indent=1))
            else:
                print(report["text"])
        else:
            report = stats(index)

            def show():
                kinds = ", ".join(f"{kind} {count}" for kind, count in sorted(report["kinds"].items()))
                print(f"{report['files']} files ({kinds}); {report['symbols']} symbols, {report['imports']} imports, "
                      f"{report['calls']} calls")
                if report["skipped"]:
                    print("not indexed: " + ", ".join(f"{key} {value}" for key, value in sorted(report["skipped"].items())))
                if report["parse_fallbacks"]:
                    print("regex fallback (did not parse): " + ", ".join(report["parse_fallbacks"][:10]))
                cache = report["cache"]
                where = "no cache (built on the fly)" if not cache else (
                    f"cache {cache['path']} ({cache['bytes']} bytes; {cache['reused']} reused, {cache['indexed']} "
                    f"indexed, {cache['removed']} removed" + (f", {len(cache['stale'])} stale" if cache["frozen"] else "")
                    + ")")
                print(f"build {report['build_seconds']} s; {where}")
            _emit(report, as_json, show)
    except BrokenPipeError:
        return 0
    except CodeIndexError as exc:
        print(f"code_index: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"code_index: {exc.strerror or exc}: {exc.filename or ''}".rstrip(": "), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
