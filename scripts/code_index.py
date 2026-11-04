#!/usr/bin/env python3
"""Regenerable, read-only code index: find, callers, import paths and affected files.

Python files are parsed with ast, never imported or run; a file this Python
cannot parse gets a regex pass instead. Markdown headings, shell functions,
JSON/TOML/YAML keys and JavaScript functions get a light name pass, and other
text files a word pass. The index is built on the fly, or kept as one JSON
file per indexed root in a cache directory you name (--cache DIR or
OAW_CODE_INDEX_CACHE); the cache records each file's size, mtime and sha256,
and a stale file is re-indexed (with --frozen: reported, not re-indexed).
Nothing is written inside the indexed tree unless you name a cache directory
there. Results are pointers to read, ranked by word statistics: not verified
facts and not model judgments.
"""

from __future__ import annotations

import argparse
import ast
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
INDEX_VERSION = 1  # Cached record layout; a cache with another value is rebuilt.
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
         ".ts": "javascript", ".tsx": "javascript"}
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


def extract(path, data):
    """Index one file's bytes: its kind, search units and (for Python) definitions, imports and calls."""
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    kind = _kind(path, data)
    text = data.decode("utf-8", errors="replace")
    lines = _lines(text)
    python, error = None, None
    if kind == "python":
        try:
            units, python = _python_record(lines, text)
        except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
            kind, error = "python-regex", f"{type(exc).__name__}: {getattr(exc, 'msg', None) or exc}"[:160]
            if getattr(exc, "lineno", None):
                error += f" (line {exc.lineno})"
            units, python = _python_fallback(lines)
    else:
        units = _other_units(kind, lines)
    kept = []
    for index, unit in enumerate(units):
        if not unit[6] and not unit[0] and index:
            continue
        unit[6] = {term: round(weight, 2) for term, weight in unit[6].items()}
        unit[7] = round(sum(unit[6].values()), 1)
        kept.append(unit)
    record = {"kind": kind, "lines": len(lines), "units": kept}
    if python is not None:
        record["py"] = python
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


def _cache_file(root, cache_dir):
    digest = hashlib.sha256(os.path.normcase(root).encode("utf-8", "surrogatepass")).hexdigest()[:16]
    return os.path.join(cache_dir, f"code-index-{digest}.json")


def _load_cache(path, root, include_generated):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if (not isinstance(data, dict) or data.get("index_version") != INDEX_VERSION or data.get("root") != root
            or data.get("include_generated") != include_generated or not isinstance(data.get("files"), dict)):
        return None
    return data["files"]


def _save_cache(path, root, include_generated, files):
    directory = os.path.dirname(path)
    data = {"index_version": INDEX_VERSION, "root": root, "include_generated": include_generated, "files": files}
    handle, temporary = tempfile.mkstemp(prefix=".code-index-", suffix=".tmp", dir=directory)
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


def build_index(root=".", cache_dir=None, frozen=False, include_generated=False):
    """Index root (on the fly, or through the cache in cache_dir) and return an Index."""
    started = time.perf_counter()
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise CodeIndexError(f"root is not a directory: {root}")
    cache_path, old = None, None
    if cache_dir:
        cache_dir = os.path.abspath(cache_dir)
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except OSError as exc:
            raise CodeIndexError(f"cannot create cache directory {cache_dir}: {exc.strerror or exc}") from None
        cache_path = _cache_file(root, cache_dir)
        old = _load_cache(cache_path, root, include_generated)
    counts, files, stale = Counter(), {}, []
    for path, full, info in _walk(root, counts, include_generated, cache_dir):
        previous = old.get(path) if old else None
        if previous and previous.get("size") == info.st_size and previous.get("mtime_ns") == info.st_mtime_ns:
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
                           "mtime_ns": info.st_mtime_ns, "sha256": None}
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
            previous["mtime_ns"], previous["size"] = info.st_mtime_ns, info.st_size
            files[path] = previous
            counts["reused"] += 1
            counts["touched"] += 1
            continue
        if b"\0" in data[:8192]:
            record = {"kind": "skipped", "reason": "binary"}
        else:
            record = extract(path, data)
        record.update(size=info.st_size, mtime_ns=info.st_mtime_ns, sha256=digest)
        files[path] = record
        counts["indexed"] += 1
    removed = sorted(set(old or ()) - set(files) - set(stale))
    if frozen:
        stale.extend(path for path in removed if path not in stale)
    if cache_path and (counts["indexed"] or counts["touched"] or removed or old is None) and not (frozen and old):
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

    # -------- paths and modules

    def tables(self):
        if self._tables is None:
            defs, by_name, module_names, var_types, classes = {}, {}, {}, {}, {}
            for path, record in self.files.items():
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
                            "var_types": var_types, "attr_types": attr_types}
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
            for suffix in (".py", "/__init__.py"):
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
                found = self.member(("module", path), qualname.split(".")) if self.files[path].get("py") else None
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
        or name.endswith("_test.py") or name == "conftest.py"


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
    return scope or "<module>"


def callers(index, symbol, limit=50):
    """Call sites of the named definition(s). Calls on receivers of unknown type that use the same name come
    after the resolved ones, those whose receiver is named like the target's class first."""
    targets, path = index.targets(symbol)
    names = {target[2].rsplit(".", 1)[-1] for target in targets}
    classes = {target for target in targets
               if index.tables()["defs"].get((target[1], target[2]), ("",))[0] == "class"}
    wanted = set(targets)
    for target in list(targets):  # Instantiating a class calls its __init__.
        if target[2].endswith(".__init__"):
            wanted.add(("def", target[1], target[2].rsplit(".", 1)[0]))
            names.add(target[2].rsplit(".", 2)[-2])
    owners = set()  # Receiver names that suggest the target's class: index.resolve() for Index.resolve.
    for target in targets:
        if "." in target[2]:
            owner = target[2].rsplit(".", 2)[-2]
            parts = _CAMEL.findall(owner)
            owners.update({owner.lower(), "_".join(parts).lower(), parts[-1].lower() if parts else ""} - {""})
    external = None
    if not targets and path is None:
        external = symbol.strip().replace("::", ".")
        names = {external.rsplit(".", 1)[-1]}
    rows = []
    for file, record in sorted(index.files.items()):
        python = record.get("py")
        if not python:
            continue
        local = names | _aliases(index, file, names)
        for line, scope, chain in python["calls"]:
            last = chain.rsplit(".", 1)[-1]
            if last not in local:
                continue
            target = index.resolve(file, scope, chain)
            if external is not None:
                if target and target[0] == "ext" and (target[1] == external or target[1].endswith("." + external)
                                                      or chain == external):
                    rows.append((0, file, line, scope))
                continue
            if target and (target in wanted or target in classes):
                rows.append((0, file, line, scope))
            elif target is None:  # Receiver type unknown (or a name nothing defines): same name only.
                receiver = chain.rsplit(".", 2)[-2].strip("_").lower() if "." in chain else ""
                rows.append((1 if receiver in owners else 2, file, line, scope))
    rows.sort()
    results = [{"path": file, "line": line, "symbol": _scope_label(scope), "resolved": rank == 0}
               for rank, file, line, scope in rows[:limit]]
    return {"schema_version": SCHEMA_VERSION, "targets": [f"{t[1]}::{t[2]}" for t in sorted(targets)]
            or ([external] if external else []), "total": len(rows), "resolved": sum(1 for row in rows if not row[0]),
            "results": results}


def import_path(index, source, target):
    """Shortest import chain from source to target; if there is none, from target back to source."""
    start, goal = index.user_path(source), index.user_path(target)
    for module in (start, goal):
        if index.files[module].get("py") is None:
            raise CodeIndexError(f"not a Python module: {module}")
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

    if index.files[path].get("py") is None:
        return {"schema_version": SCHEMA_VERSION, "target": path, "note": "only Python imports and calls are tracked",
                "results": []}
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
            return {"schema_version": SCHEMA_VERSION, "target": f"{path}::{qualname}",
                    "note": "no such definition", "results": []}
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
                if scope and (file, scope) in defs:
                    for other, line, where, label in _symbol_sites(index, ("def", file, scope)):
                        add(other, line, where, label + f" (via {file}::{scope})", 2)
                else:
                    for other, found in sorted(edges.items()):
                        for line, where, imported, label in sorted(found):
                            if imported == file:
                                add(other, line, where, label + f" (via {file})", 2)
    rows.sort(key=lambda row: (row["hop"], row["path"]))
    return {"schema_version": SCHEMA_VERSION, "target": path + (f"::{chain.replace('::', '.')}" if separator else ""),
            "total": len(rows), "results": rows[:limit]}


def _aliases(index, path, names):
    """Local names that `from module import name as alias` binds to one of names."""
    return {alias for alias, bound in index.bindings(path).items()
            if isinstance(bound, tuple) and bound[0] == "symbol" and bound[2] in names}


def _symbol_sites(index, target):
    """(file, line, scope, label) where a definition is called, imported by name, or referenced as module.name."""
    defs = index.tables()["defs"]
    name = target[2].rsplit(".", 1)[-1]
    unique = len(index.tables()["by_name"].get(name, ())) == 1
    is_class = defs.get((target[1], target[2]), ("",))[0] == "class"
    sites = []
    for file, record in sorted(index.files.items()):
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


def stats(index):
    kinds = Counter(record.get("kind", "?") for record in index.files.values())
    symbols = imports = calls = 0
    for record in index.files.values():
        python = record.get("py")
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
            size = os.path.getsize(info["cache"])
        except OSError:
            size = None
        cache = {"path": info["cache"], "bytes": size, "reused": info["counts"].get("reused", 0),
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
    shown, total = len(rows), report.get("total", len(rows))
    if total > shown:
        print(f"... {total - shown} more (raise --limit)")
    if verb == "callers" and any(not row.get("resolved", True) for row in rows):
        print("~ = same name on a receiver whose type is not known; check before relying on it")


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
                        help=f"keep the index in DIR and refresh stale files (default: ${CACHE_ENV}, else no cache)")
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
  stats                               Files, symbols, build time and cache state

The index is rebuilt from source on every run unless --cache names a directory
outside (or deliberately inside) the tree. Agents read it; nothing writes it
except this command. Results are pointers to check in the source.
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
    args = parser().parse_args(argv)
    as_json = getattr(args, "json", False)
    try:
        index = build_index(getattr(args, "root", "."), getattr(args, "cache", None) or os.environ.get(CACHE_ENV),
                            getattr(args, "frozen", False), getattr(args, "include_generated", False))
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
                    return
                print(f"{report['total']} files affected by {report['target']} ({args.hops} hop"
                      + ("s" if args.hops > 1 else "") + ")")
                _print_sites(index, report, "affected")
            _emit(report, as_json, show)
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
