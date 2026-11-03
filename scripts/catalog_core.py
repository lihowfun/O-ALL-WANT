"""Pure catalog functions for OAW skill digestion (prototype v0).

No network, no subprocess and no file writes happen here. Every food byte is
data: it is decoded and pattern-matched, never imported, executed or rendered.

- `normalize_source()` / `dedupe_sources()`: one repository is one food.
- `static_scan()`: deterministic T0 checks over in-memory files. Static rules
  only raise flags; a "toxic" verdict always needs an owner decision.
- `derive()`: food headline and per-component dispositions from evidence and
  owner decisions. Popularity (stars, author, downloads, requested_by) is not an
  input, and imported reports are historical-prior data that cannot raise it.
- `build_name()`, `install_inventory()`, `effect_vs_default()`, `decide_plan()`
  and `build_view()` feed the CLI and every renderer.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import PurePosixPath
import re
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

SCHEMA_VERSION = 1
RELEASE = "2.0.0"
SCANNER_VERSION = 1
VERDICT_RULES_VERSION = 1
VIEW_SCHEMA = "oaw-catalog-view/1"

# code: (symbol, ascii, English, Traditional Chinese)
VERDICTS = {
    "nutritious": ("●", "[+]", "nutritious", "營養"),
    "no-gain": ("＝", "[=]", "no gain", "沒營養"),
    "untested": ("○", "[ ]", "untested", "未測"),
    "incomplete": ("◌", "[?]", "incomplete evidence", "證據不完整"),
    "regressed": ("▼", "[v]", "regressed", "變差"),
    "diarrhea": ("◐", "[~]", "diarrhea", "拉肚子"),
    "risky": ("▲", "[!]", "risky", "有疑慮"),
    "toxic": ("✖", "[X]", "toxic", "有毒"),
    "inedible": ("⊘", "[/]", "inedible", "不能吃"),
}
HEADLINE_PRIORITY = ("toxic", "inedible", "risky", "regressed", "diarrhea", "incomplete", "no-gain", "nutritious", "untested")
EVIDENCE_LEVELS = {
    "measured": "measured by a consented live run",
    "static-measured": "measured from files without running anything",
    "not-measured": "not measured",
    "historical-prior": "imported historical report; never counted in a verdict",
}
LIVE_PROVENANCE = ("runner-live", "operator-run")
DISPOSITIONS = {"absorb": ("green", "吸收"), "excrete": ("red", "排掉"), "hold": ("amber", "暫留")}
DECISION_KINDS = ("triage", "absorb", "excrete", "remove", "block", "reject")
TRIAGE_OUTCOMES = ("benign", "allergen", "confirm-toxic")
POPULARITY_FIELDS = ("stars", "stargazers_count", "author", "downloads", "requested_by", "official", "forks",
                     "watchers", "popularity", "scout", "intake")
LIMITS = {"max_files": 5000, "max_total_bytes": 50 * 1024 * 1024, "max_file_bytes": 5 * 1024 * 1024,
          "max_path": 240, "skill_body_bytes": 24000}
TOKENS_PER_RUN = (600_000, 900_000)
TOKEN_LABEL = "estimate: about 0.6-0.9M logical tokens per tool-using agent run"
SANDBOX_CONDITIONS = ("isolated-venv", "project-copy", "no-api-keys", "no-network", "disposable-vm")
INSTALL_ALLOWED_SUFFIXES = (".md", ".txt")
ROUTER_NAMES = ("claude.md", "agents.md", "gemini.md", ".cursorrules", ".windsurfrules", "copilot-instructions.md")
READ_ONLY_TOOLS = {"read", "grep", "glob", "ls"}

_HEX64 = re.compile(r"[0-9a-f]{64}")
_UNSAFE_TEXT = re.compile("[\x00-\x1f\x7f-\x9f\u061c\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff"
                          "\U000e0000-\U000e007f]")
_HIDDEN = re.compile("[\u061c\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\U000e0000-\U000e007f]")
_RESERVED = {"con", "prn", "aux", "nul"} | {f"{p}{n}" for p in ("com", "lpt") for n in range(1, 10)}


class SourceError(ValueError):
    """An input that is not a supported food source."""


# --------------------------------------------------------------------------- hashing / text

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def record_sha256(value) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def tree_sha256(file_hashes: dict) -> str:
    """Hash of sorted "<sha256>  <path>" lines over the received bytes."""
    return sha256_bytes("".join(f"{h}  {p}\n" for p, h in sorted(file_hashes.items())).encode("utf-8"))


def sanitize_text(value, limit: int = 200) -> str:
    """Food-derived text for terminals and HTML builders: no controls, bidi or zero-width."""
    text = _UNSAFE_TEXT.sub(" ", unicodedata.normalize("NFC", str(value if value is not None else "")))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: max(0, limit - 1)].rstrip() + "…"


def display_name(name: str) -> str:
    return name if isinstance(name, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name) else "id#" + sha256_bytes(str(name).encode())[:8]


def slug(value: str, limit: int = 64) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value).casefold()).strip("-")
    return (text[:limit].strip("-") or "food")


def _normalized(text: str) -> str:
    """Matching form: NFKC, casefold, format (Cf) characters removed."""
    text = unicodedata.normalize("NFKC", text).casefold()
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf")


# --------------------------------------------------------------------------- sources

def normalize_source(text: str) -> dict:
    """Canonical identity of a food source. The key ignores case, .git, slashes and refs."""
    raw = str(text or "").strip()
    if not raw or len(raw) > 512 or any(ch.isspace() for ch in raw) or _UNSAFE_TEXT.search(raw):
        raise SourceError(f"Not a repository URL: {sanitize_text(raw, 80)!r}")
    if raw.casefold().startswith("file://"):
        parts = urlsplit(raw)
        if parts.netloc not in ("", "localhost") or parts.query or parts.fragment:
            raise SourceError("Only local file:// repository paths are supported.")
        path = unquote(parts.path).rstrip("/")
        if not path or ".." in path.split("/"):
            raise SourceError("Unsafe file:// repository path.")
        name = path.rsplit("/", 1)[-1]
        name = name[:-4] if name.casefold().endswith(".git") and len(name) > 4 else name
        key = "file://" + path
        return {"key": key, "kind": "file", "owner": None, "repo": name, "display": "local/" + name,
                "url": key, "fetch_url": "file://" + path, "ref": None, "subdir": None}
    ref = subdir = None
    match = re.fullmatch(r"(?i)git@github\.com:([^/]+)/([^/]+?)/?", raw)
    if match:
        owner, repo, rest = match.group(1), match.group(2), []
    else:
        if re.match(r"(?i)^(?:https?|ssh|git)://", raw):
            parts = urlsplit(raw)
        elif re.match(r"(?i)^(?:www\.)?github\.com/", raw):
            parts = urlsplit("https://" + raw)
        elif re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+/?", raw):
            parts = urlsplit("https://github.com/" + raw)
        else:
            raise SourceError(f"Not a GitHub repository: {sanitize_text(raw, 80)!r}")
        if parts.scheme.casefold() not in ("https", "http", "ssh", "git") or (parts.hostname or "").casefold() not in ("github.com", "www.github.com"):
            raise SourceError(f"Only github.com repositories are supported: {sanitize_text(raw, 80)!r}")
        segments = [unquote(s) for s in parts.path.split("/") if s]
        if len(segments) < 2:
            raise SourceError(f"URL lacks OWNER/REPO: {sanitize_text(raw, 80)!r}")
        owner, repo, rest = segments[0], segments[1], segments[2:]
    if repo.casefold().endswith(".git"):
        repo = repo[:-4]
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", owner) or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", repo) or repo in (".", ".."):
        raise SourceError(f"Invalid GitHub OWNER/REPO: {sanitize_text(owner + '/' + repo, 80)!r}")
    if len(rest) >= 2 and rest[0] in ("tree", "blob") and re.fullmatch(r"[A-Za-z0-9._/-]{1,200}", rest[1]):
        ref = rest[1]
        subdir = "/".join(rest[2:]) or None
    return {"key": f"github.com/{owner.casefold()}/{repo.casefold()}", "kind": "github", "owner": owner, "repo": repo,
            "display": f"{owner}/{repo}", "url": f"https://github.com/{owner}/{repo}",
            "fetch_url": f"https://github.com/{owner}/{repo}.git", "ref": ref, "subdir": subdir}


def dedupe_sources(inputs) -> dict:
    """Group a batch by canonical key; report merges and unusable inputs."""
    foods, errors = {}, []
    for item in inputs:
        try:
            source = normalize_source(item)
        except SourceError as exc:
            errors.append({"input": sanitize_text(item, 120), "error": str(exc)})
            continue
        entry = foods.setdefault(source["key"], {"source": source, "inputs": []})
        entry["inputs"].append(str(item).strip())
    merges = [{"key": key, "inputs": entry["inputs"]} for key, entry in foods.items() if len(entry["inputs"]) > 1]
    return {"foods": list(foods.values()), "merges": merges, "errors": errors}


def food_id(source: dict, taken: dict) -> str:
    """Short, stable registry id; `taken` maps existing ids to canonical keys."""
    for candidate in (slug(source["repo"]), slug(f"{source.get('owner') or 'local'}-{source['repo']}")):
        if taken.get(candidate) in (None, source["key"]):
            return candidate
    return slug(source["repo"], 55) + "-" + sha256_bytes(source["key"].encode())[:8]


# --------------------------------------------------------------------------- archive members

def member_path_error(path: str, seen_casefold: set | None = None):
    """Why a food path cannot enter the sealed tar, or None."""
    if not isinstance(path, str) or not path:
        return "empty path"
    if len(path) > LIMITS["max_path"]:
        return "path too long"
    if "\\" in path or ":" in path or path.startswith("/") or _UNSAFE_TEXT.search(path):
        return "unsafe characters"
    for part in path.split("/"):
        if part in ("", ".", ".."):
            return "unsafe segment"
        if part.split(".")[0].casefold() in _RESERVED or part.rstrip(". ") != part:
            return "reserved Windows name"
    if seen_casefold is not None:
        folded = path.casefold()
        if folded in seen_casefold:
            return "case collision"
        seen_casefold.add(folded)
    return None


# --------------------------------------------------------------------------- T0 static checks

_SCRIPT_SUFFIXES = {".py", ".pyw", ".sh", ".bash", ".zsh", ".fish", ".js", ".mjs", ".cjs", ".ts", ".mts", ".cts",
                    ".tsx", ".jsx", ".ps1", ".psm1", ".bat", ".cmd", ".rb", ".pl", ".php", ".lua", ".go", ".rs",
                    ".java", ".kt", ".swift", ".c", ".cc", ".cpp", ".cs", ".vbs", ".pth"}
_CONFIG_SUFFIXES = {".json", ".jsonc", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".xml", ".env", ".lock"}
_DOC_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ".adoc", ".org"}
_ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp", ".pdf", ".woff", ".woff2",
                   ".ttf", ".otf", ".mp3", ".mp4", ".wav", ".webm", ".mov", ".zip", ".gz", ".tgz"}
_MANIFESTS = {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "pyproject.toml",
              "setup.py", "setup.cfg", "pipfile", "pipfile.lock", "poetry.lock", "uv.lock", "cargo.toml",
              "cargo.lock", "go.mod", "go.sum", "gemfile", "gemfile.lock", "composer.json", "dockerfile",
              "docker-compose.yml", "docker-compose.yaml", "compose.yaml", "makefile", "deno.json"}
_BINARY_MAGIC = (b"\x7fELF", b"\0asm", b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xfe\xed\xfa\xce", b"\xca\xfe\xba\xbe")
_IMPORT_HOOKS = {"sitecustomize.py", "usercustomize.py", "conftest.py"}

_HOST_SETTINGS = r"\.claude/settings(?:\.local)?\.json|\.claude\.json\b|\.codex/(?:config\.toml|hooks\.json)|\b(?:claude|codex)\s+mcp\s+add\b|\.mcp\.json\b"
_GLOBAL = r"git\s+config\s+--global|npm\s+config\s+set|\.bashrc\b|\.zshrc\b|\.bash_profile\b|\bsetx\s|\.gitconfig\b"
_HOME = r"(?:^|[\s\"'(=])~/|\$home\b|%userprofile%|%appdata%|\$env:userprofile|expanduser\(|path\.home\(\)|os\.homedir\(\)"
_UPDATE = (r"\bgit\s+pull\b|\bnpm\s+(?:update|i(?:nstall)?\s+(?:-g|--global))\b|\bpip3?\s+install\s+(?:-u\b|--upgrade)"
           r"|\buv\s+tool\s+(?:install|upgrade)\b|\bself[-_ ]?update\b|\bauto[-_ ]?updat\w*|\bbrew\s+upgrade\b")
_BACKGROUND = (r"\bnohup\b|\bsetsid\b|\bdisown\b|\bstart\s+/b\b|start_new_session\s*=\s*true|detached\s*:\s*true"
               r"|\bpm2\s+start\b|\bdaemoni[sz]e\b|\bdaemon\s*[:=]\s*true|\bsystemctl\s+(?:enable|start)\b|\blaunchctl\b|\bcrontab\b|\bschtasks\b")
_NETWORK = (r"\b(?:curl|wget)\b|urllib\.request|\brequests\.(?:get|post|put|patch|delete|session)\b|http\.client"
            r"|\bfetch\s*\(|\baxios\b|socket\.socket|invoke-webrequest|invoke-restmethod|\bhttpx\b|\baiohttp\b|xmlhttprequest|\bwebsocket\b"
            r"|^\s*(?:import|from)\s+(?:requests|httpx|aiohttp|urllib3|websockets?)\b")
_MODEL = (r"\bclaude\s+-p\b|\bcodex\s+exec\b|api\.anthropic\.com|api\.openai\.com|generativelanguage\.googleapis\.com"
          r"|^\s*(?:import|from)\s+(?:anthropic|openai|litellm)\b|@anthropic-ai/(?:sdk|claude-agent-sdk|claude-code)|require\(['\"]openai['\"]\)")
_WRITE_INSTRUCTIONS = r"\b(?:append|write|add|insert|inject|update)\w*\b[^\n]{0,60}\b(?:claude|agents|gemini)\.md\b"
_PIPE = r"\b(?:curl|wget|iwr|invoke-webrequest)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|da)?sh\b|\|\s*iex\b"
_EXEC = (r"\b(?:eval|exec)\s*\(\s*(?:base64|b64decode|atob|codecs\.decode|bytes\.fromhex|zlib\.decompress|requests\.|urllib|fetch\s*\()"
         r"|base64\s+(?:-d|--decode)\b[^\n]*\|\s*(?:ba)?sh\b|__import__\(\s*['\"]base64")

_SEV = {
    "critical": {"auto-exec": "high", "executable": "high", "instruction": "high", "manifest": "high", "config": "medium", "other": "medium"},
    "host": {"auto-exec": "high", "executable": "high", "instruction": "medium", "manifest": "medium", "config": "medium", "other": "low"},
    "behaviour": {"auto-exec": "high", "executable": "medium", "instruction": "medium", "manifest": "medium", "config": "low", "other": "low"},
    "surface": {"auto-exec": "medium", "executable": "low", "instruction": "low", "manifest": "low", "config": "low", "other": "low"},
}
# (rule, pattern, severity table, allergen, meaning)
RULES = (
    ("F-PIPE", _PIPE, "critical", "network", "pipes a download into a shell"),
    ("F-EXEC", _EXEC, "critical", None, "executes decoded or downloaded code"),
    ("F-HOST", _HOST_SETTINGS, "host", "host-settings", "touches host agent settings or MCP registration"),
    ("F-GLOBAL", _GLOBAL, "host", "writes-outside-project", "touches global user configuration"),
    ("F-UPDATE", _UPDATE, "behaviour", "auto-update", "updates or installs software by itself"),
    ("F-BG", _BACKGROUND, "behaviour", "background-process", "starts a background or scheduled process"),
    ("F-WRITE-INSTR", _WRITE_INSTRUCTIONS, "behaviour", "writes-instructions", "writes agent instruction files"),
    ("S-HOME", _HOME, "surface", "writes-outside-project", "refers to the home directory"),
    ("S-NET", _NETWORK, "surface", "network", "network primitive"),
    ("S-MODEL", _MODEL, "surface", "spawns-model-calls", "calls a model by itself"),
)
_COMPILED = tuple((rule, re.compile(pattern, re.MULTILINE), table, allergen, meaning) for rule, pattern, table, allergen, meaning in RULES)
_ANY_RULE = re.compile("|".join(f"(?:{pattern})" for _rule, pattern, *_ in RULES), re.MULTILINE)
EXCLUSIONS = {
    "vector-db": ("chromadb", "faiss", "faiss-cpu", "faiss-gpu", "lancedb", "qdrant-client", "pgvector", "weaviate-client",
                  "pymilvus", "pinecone", "pinecone-client", "sqlite-vec", "sqlite-vss", "hnswlib", "usearch", "@lancedb/lancedb",
                  "chromadb-client", "vectordb"),
    "graph-memory": ("neo4j", "kuzu", "falkordb", "graphiti", "graphiti-core", "memgraph", "py2neo"),
    "second-model-runtime": ("ollama", "llama-cpp-python", "llama_cpp", "vllm", "transformers", "torch", "onnxruntime",
                             "sentence-transformers", "mlx", "ctransformers", "gpt4all", "node-llama-cpp", "@xenova/transformers"),
}
SKILL_CHECKS = ("S-ID", "S-ROLE", "S-LIC", "S-STR", "S-KIND", "S-DEP", "S-MODEL", "S-EXCL", "S-FLAG", "S-NET", "S-BUD", "S-HOOK", "S-MCP", "S-NEST", "S-SHADOW")


def file_role(path: str, data: bytes, mode: str | None = None) -> str:
    """S-ROLE: binary, instruction, manifest, executable, config, docs, asset or other."""
    pure = PurePosixPath(path)
    name, suffix = pure.name.casefold(), pure.suffix.casefold()
    parents = [p.casefold() for p in pure.parts[:-1]]
    if data.startswith(_BINARY_MAGIC) or data[:2] == b"MZ" and suffix in ("", ".exe", ".dll", ".bin"):
        return "binary"
    if suffix in _ASSET_SUFFIXES:
        return "asset"
    if b"\0" in data[:8192]:
        return "binary"
    if name == "skill.md" or name in ROUTER_NAMES or (suffix == ".md" and parents and parents[-1] in ("agents", "commands")):
        return "instruction"
    if name in _MANIFESTS or re.fullmatch(r"requirements[\w.-]*\.txt", name):
        return "manifest"
    if mode == "100755" or data.startswith(b"#!") or suffix in _SCRIPT_SUFFIXES:
        return "executable"
    if suffix in _CONFIG_SUFFIXES:
        return "config"
    if (suffix in _DOC_SUFFIXES or (parents and parents[0] in ("docs", "doc")) or
            re.match(r"(?:readme|license|licence|copying|notice|changelog|contributing|authors|security)\b", name)):
        return "docs"
    return "other"


def parse_frontmatter(text: str):
    """Restricted YAML subset: top-level `key: value` and folded/literal blocks."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, text
    fields, key = {}, None
    for line in lines[1:end]:
        match = re.match(r"([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if match and not line[:1].isspace():
            key, value = match.group(1).casefold(), match.group(2).strip()
            fields[key] = "" if value in ("|", ">", "|-", ">-") else value.strip("'\"")
        elif key and line[:1].isspace():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields, "\n".join(lines[end + 1:])


def detect_license(files: dict) -> dict:
    """S-LIC: normalized license text against a few SPDX signatures."""
    candidates = sorted(p for p in files if "/" not in p and re.match(r"(?i)(?:license|licence|copying|unlicense)(?:[.-].*)?$", p))
    signatures = (
        ("AGPL-3.0", ("gnu affero general public license",)), ("LGPL-3.0", ("gnu lesser general public license",)),
        ("GPL-3.0", ("gnu general public license", "version 3")), ("GPL-2.0", ("gnu general public license", "version 2")),
        ("Apache-2.0", ("apache license", "version 2.0")), ("MPL-2.0", ("mozilla public license",)),
        ("MIT", ("permission is hereby granted, free of charge",)),
        ("BSD-3-Clause", ("redistribution and use in source and binary forms", "neither the name")),
        ("BSD-2-Clause", ("redistribution and use in source and binary forms",)),
        ("ISC", ("permission to use, copy, modify, and/or distribute this software",)),
        ("Unlicense", ("this is free and unencumbered software",)),
    )
    found = []
    for path in candidates:
        text = re.sub(r"\s+", " ", _normalized(files[path].decode("utf-8", "replace")))
        for spdx, needles in signatures:
            if all(needle in text for needle in needles):
                found.append({"spdx": spdx, "file": path, "sha256": sha256_bytes(files[path])})
                break
        else:
            found.append({"spdx": "unknown", "file": path, "sha256": sha256_bytes(files[path])})
    permissive = {"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "ISC", "Unlicense", "MPL-2.0"}
    known = [item for item in found if item["spdx"] != "unknown"]
    if not found:
        return {"spdx": None, "files": [], "distribution": "unknown"}
    spdx = " AND ".join(sorted({item["spdx"] for item in known})) or "unknown"
    distribution = ("redistributable" if known and all(i["spdx"] in permissive for i in known)
                    else "local-only" if known else "unknown")
    return {"spdx": spdx, "files": found, "distribution": distribution}


def _json(data: bytes):
    try:
        value = json.loads(data.decode("utf-8-sig"))
    except (ValueError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def _hook_commands(config: dict):
    """Yield (event, command) from Claude/Codex style hooks objects."""
    hooks = config.get("hooks", config)
    if not isinstance(hooks, dict):
        return
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            inner = group.get("hooks") if isinstance(group.get("hooks"), list) else [group]
            for hook in inner:
                if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                    yield str(event), hook["command"]


def _declared_deps(path: str, data: bytes) -> list:
    name = PurePosixPath(path).name.casefold()
    text = data.decode("utf-8", "replace")
    found = []
    if name == "package.json":
        value = _json(data) or {}
        for field in ("dependencies", "peerDependencies", "optionalDependencies"):
            if isinstance(value.get(field), dict):
                found.extend((dep, str(spec)) for dep, spec in value[field].items())
    elif re.fullmatch(r"requirements[\w.-]*\.txt", name):
        for line in text.splitlines():
            match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)(.*)", line)
            if match and not line.lstrip().startswith(("#", "-")):
                found.append((match.group(1), match.group(2).strip()))
    elif name in ("pyproject.toml", "setup.py", "setup.cfg"):
        block = re.search(r"(?:^|\n)\s*(?:dependencies|install_requires)\s*=\s*\[(.*?)\]", text, re.S)
        for item in re.findall(r"['\"]([A-Za-z0-9][A-Za-z0-9._-]*)([^'\"]*)['\"]", block.group(1) if block else ""):
            found.append(item)
    return [(dep.casefold().replace("_", "-"), spec) for dep, spec in found]


def _code_imports(path: str, text: str) -> set:
    suffix = PurePosixPath(path).suffix.casefold()
    names = set()
    if suffix in (".py", ".pyw"):
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    names.add(node.module.split(".")[0])
    elif suffix in (".js", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".tsx", ".jsx"):
        for match in re.finditer(r"(?:require\(\s*|\bfrom\s+|\bimport\s+)['\"]([^'\"./][^'\"]*)['\"]", text):
            spec = match.group(1)
            names.add("/".join(spec.split("/")[:2]) if spec.startswith("@") else spec.split("/")[0])
    return {name.casefold().replace("_", "-") for name in names if name}


def _command_paths(command: str, paths) -> set:
    """Files a hook/MCP/lifecycle command refers to (suffix match, never resolved on disk)."""
    referenced = set()
    for token in re.findall(r"[\w${}.@%/\\-]+\.(?:sh|bash|py|js|mjs|cjs|ts|ps1|bat|cmd|rb|pl)\b", command):
        token = re.sub(r"^(?:\$\{[^}]+\}|\$[A-Za-z_]+|%[^%]+%)[/\\]?", "", token).replace("\\", "/").lstrip("./")
        if token:
            referenced.update(p for p in paths if p == token or p.endswith("/" + token))
    return referenced


def static_scan(files: dict, *, food: str, commit: str | None = None, integrity: str = "unknown",
                modes: dict | None = None, skipped=(), symlinks: dict | None = None, gitlinks=()) -> dict:
    """Deterministic T0 record. Flags only; nothing here can mark a food toxic."""
    modes, symlinks = modes or {}, symlinks or {}
    paths = sorted(files)
    roles = {p: file_role(p, files[p], modes.get(p)) for p in paths}
    flags, counters, info_matches, truncated = [], {}, 0, 0
    allergens, hosts = set(), set()

    def flag(rule, severity, path, line, matched, allergen=None, meaning=""):
        nonlocal truncated
        if allergen:
            allergens.add(allergen)
        key = (rule, path)
        counters[key] = counters.get(key, 0) + 1
        if counters[key] > 3 or len(flags) >= 400:
            truncated += 1
            return
        flags.append({"id": f"{rule}:{path}:{line}", "rule": rule, "severity": severity, "path": path, "line": line,
                      "role": roles.get(path, "auto-exec"), "allergen": allergen, "meaning": meaning,
                      "match_sha256": sha256_bytes(matched.encode("utf-8"))})

    # Declared executable surfaces: hooks, MCP servers, plugin manifests, package lifecycle scripts.
    hooks, mcp, plugins, auto_exec, lifecycle = [], [], [], {}, []
    for path in paths:
        name = PurePosixPath(path).name.casefold()
        if roles[path] not in ("config", "manifest"):
            continue
        config = _json(files[path]) if name.endswith(".json") else None
        if config is None:
            continue
        is_plugin = name == "plugin.json" or name == "marketplace.json" or ".claude-plugin" in path or ".codex-plugin" in path
        if is_plugin:
            plugins.append({"path": path, "hooks": "hooks" in config, "mcp": "mcpServers" in config,
                            "declares": sorted(k for k in ("skills", "commands", "agents", "hooks", "mcpServers") if k in config)})
        if name == "hooks.json" or (name.startswith("settings") and ".claude/" in path) or (is_plugin and isinstance(config.get("hooks"), dict)):
            for event, command in _hook_commands(config):
                hooks.append({"path": path, "event": sanitize_text(event, 60), "command": command})
        servers = config.get("mcpServers") if isinstance(config.get("mcpServers"), dict) else None
        if servers is not None and (name in (".mcp.json", "mcp.json") or is_plugin or name.endswith("settings.json")):
            for server, spec in servers.items():
                spec = spec if isinstance(spec, dict) else {}
                command = " ".join(str(x) for x in [spec.get("command", ""), *(spec.get("args") or [])] if isinstance(x, (str, int)))
                mcp.append({"path": path, "name": sanitize_text(server, 64), "command": command, "remote": bool(spec.get("url"))})
        if name == "package.json" and isinstance(config.get("scripts"), dict):
            for script, command in config["scripts"].items():
                if script in ("preinstall", "install", "postinstall", "prepare", "prepublish", "preprepare", "postprepare") and isinstance(command, str):
                    lifecycle.append({"path": path, "script": script, "command": command})
    for item in hooks + mcp + lifecycle:
        for referenced in _command_paths(item["command"], paths):
            auto_exec.setdefault(referenced, item["path"])
    for item in hooks + mcp + lifecycle:
        normalized = _normalized(item["command"])
        for rule, pattern, table, allergen, meaning in _COMPILED:
            match = pattern.search(normalized)
            if match:
                flag(rule, _SEV[table]["auto-exec"], item["path"], 0, match.group(0), allergen, meaning + " (auto-run command)")
        if re.search(r"\bnpx\s+(?:-y|--yes)\s+(?!\S*@\d)\S+|\buvx\s+(?!\S*==)\S+|\bpip3?\s+install\s+(?!\S*==)[a-z]", normalized):
            flag("S-DEP", "medium", item["path"], 0, normalized[:200], "unpinned-deps", "auto-run command uses unpinned packages")
    events = sorted({h["event"] for h in hooks})
    if hooks:
        allergens.add("hooks")
        for path in sorted({h["path"] for h in hooks}):
            flag("S-HOOK", "medium", path, 0, path, "hooks", "declares auto-executing hooks")
        context = sorted(e for e in events if e.casefold() in ("sessionstart", "userpromptsubmit", "precompact", "subagentstart"))
        for event in context:
            flag("S-HOOK-CTX", "medium", next(h["path"] for h in hooks if h["event"] == event), 0, event, "writes-context",
                 f"{event} hook injects text into every session or prompt")
    if mcp:
        allergens.add("mcp")
        for server in mcp:
            flag("S-MCP", "medium", server["path"], 0, server["name"], "mcp", "declares an MCP server")
    for item in lifecycle:
        flag("S-LIFECYCLE", "medium", item["path"], 0, item["script"], "package-install", f"package {item['script']} script runs on install")

    # Line rules over text roles; docs only get the hidden-character check.
    declared, imported = [], set()
    for path in paths:
        role = "auto-exec" if path in auto_exec else roles[path]
        if role in ("binary", "asset"):
            continue
        raw = files[path].decode("utf-8", "replace")
        hidden = _HIDDEN.search(raw[1:] if raw.startswith("\ufeff") else raw)
        if hidden:
            line = raw.count("\n", 0, hidden.start() + (1 if raw.startswith("\ufeff") else 0)) + 1
            severity = {"docs": "low", "other": "medium"}.get(role, "high")
            flag("F-HID", severity, path, line, "U+%04X" % ord(hidden.group(0)), None, "hidden or bidirectional control characters")
        if role == "docs":
            continue
        if roles[path] == "manifest":
            declared.extend(_declared_deps(path, files[path]))
        if roles[path] == "executable":
            imported |= _code_imports(path, raw)
        normalized = _normalized(raw)
        hosts.update(h for h in re.findall(r"https?://([a-z0-9][a-z0-9.-]{0,200}[a-z0-9])", normalized) if "." in h)
        if not _ANY_RULE.search(normalized):
            continue
        sev_role = role if role in _SEV["critical"] else "other"
        for number, line in enumerate(normalized.split("\n"), 1):
            for rule, pattern, table, allergen, meaning in _COMPILED:
                match = pattern.search(line)
                if match:
                    flag(rule, _SEV[table][sev_role], path, number, match.group(0), allergen, meaning)

    # Import hooks, stdlib shadows and build backends would run if the tree were placed on sys.path.
    stdlib = set(getattr(sys, "stdlib_module_names", ())) - {"__future__"}
    for path in paths:
        name = PurePosixPath(path).name
        folded = name.casefold()
        if folded in _IMPORT_HOOKS or folded.endswith(".pth") or (folded.endswith(".py") and name[:-3] in stdlib):
            flag("S-SHADOW", "medium", path, 0, name, "import-hook", "would run on Python import or startup if placed on sys.path")
        elif folded == "setup.py":
            flag("S-BUILD", "medium", path, 0, name, "package-install", "build backend code runs on install")
        if folded in ROUTER_NAMES:
            flag("S-NEST", "medium", path, 0, name, "nested-instructions", "nested always-loaded instruction file")
    for path, target in sorted(symlinks.items()):
        flag("F-LINK", "low", path, 0, str(target), None, "symlink recorded, not followed")
    for path in sorted(gitlinks):
        flag("F-ARC", "low", path, 0, path, None, "submodule recorded, not fetched")
    for path in sorted(skipped):
        flag("F-PARTIAL", "medium", path, 0, path, None, "file over the size limit was not stored or scanned")

    # S-DEP / S-EXCL / S-MODEL over declared packages and code imports (text only; nothing installed).
    local = {PurePosixPath(p).stem.casefold().replace("_", "-") for p in paths if p.endswith(".py")}
    local |= {PurePosixPath(p).parts[0].casefold().replace("_", "-") for p in paths if "/" in p}
    deps = sorted({dep for dep, _spec in declared} | (imported - local))
    non_stdlib = sorted(d for d in deps if d.replace("-", "_") not in stdlib and d not in stdlib)
    exclusions = sorted({category for category, names in EXCLUSIONS.items() for name in names if name in non_stdlib})
    for category in exclusions:
        flag("S-EXCL", "medium", "(dependencies)", 0, category, "excluded:" + category,
             f"V2 exclusion: {category} (local placement only until the owner lifts it)")
    if any(d in non_stdlib for d in ("anthropic", "openai", "litellm", "@anthropic-ai/sdk", "@anthropic-ai/claude-agent-sdk", "google-generativeai")):
        allergens.add("spawns-model-calls")
    if non_stdlib:
        allergens.add("non-stdlib-deps")
    self_rewrite = any(re.search(r"self[- ]?(?:improv|rewrit|modif|evolv)", _normalized(files[p].decode("utf-8", "replace")))
                       for p in paths if roles[p] in ("instruction", "executable"))
    if self_rewrite and "background-process" in allergens:
        exclusions = sorted(set(exclusions) | {"self-rewriting-daemon"})
        flag("S-EXCL", "medium", "(behaviour)", 0, "self-rewriting-daemon", "excluded:self-rewriting-daemon",
             "V2 exclusion: background self-rewriting process")

    license_info = detect_license(files)
    if license_info["distribution"] == "unknown":
        flag("S-LIC", "medium", license_info["files"][0]["file"] if license_info["files"] else "(root)", 0,
             str(license_info["spdx"]), None, "no recognised license: redistribution not established")

    components = _split_components(files, roles, modes, flags, hooks, mcp, plugins, auto_exec, skipped)
    skills = [c["skill"] | {"component": c["id"]} for c in components if c["kind"] == "skill"]
    for component in components:
        skill = component.get("skill")
        if skill and skill["body_bytes"] > LIMITS["skill_body_bytes"]:
            flag("S-BUD", "low", skill["path"], 0, str(skill["body_bytes"]), None,
                 f"skill body {skill['body_bytes']} bytes > {LIMITS['skill_body_bytes']}")
    flag_index = {}
    for item in flags:
        flag_index.setdefault(item["path"], []).append(item["id"])
    for component in components:
        component["flag_ids"] = sorted({fid for p in component["paths"] for fid in flag_index.get(p, [])})
    digestible = any(c["kind"] in ("skill", "agent", "command", "plugin-manifest", "hook-set", "mcp-server") for c in components)
    exec_rank = {"X0": 0, "X1-inline": 1, "X1": 2, "X2": 3}
    exec_class = max((c["exec_class"] for c in components), key=exec_rank.get, default="X0")
    by_role = {}
    for path in paths:
        by_role[roles[path]] = by_role.get(roles[path], 0) + 1
    hashes = {p: sha256_bytes(files[p]) for p in paths}
    record = {
        "schema_version": SCHEMA_VERSION, "food": food, "commit": commit, "tier": "T0", "mode": "deterministic",
        "provenance": "deterministic", "level": "static-measured", "scanner_version": SCANNER_VERSION,
        "evidence_id": f"{food}@{(commit or 'unverified')[:12]}/T0/s{SCANNER_VERSION}",
        "integrity": integrity, "tree_sha256": tree_sha256(hashes),
        "counts": {"files": len(paths), "bytes": sum(len(files[p]) for p in paths), "by_role": by_role,
                   "skipped": len(list(skipped)), "symlinks": len(symlinks), "gitlinks": len(list(gitlinks))},
        "checks_run": list(SKILL_CHECKS), "license": license_info, "exec_class": exec_class,
        "allergens": sorted(allergens), "flags": flags, "flags_truncated": truncated, "info_matches": info_matches,
        "hooks": {"count": len(hooks), "events": events}, "mcp_servers": sorted({m["name"] for m in mcp}),
        "plugins": [p["path"] for p in plugins], "network_hosts": sorted(sanitize_text(h, 120) for h in hosts)[:100],
        "dependencies": {"declared": sorted({d for d, _s in declared}), "non_stdlib": non_stdlib[:200]},
        "exclusions": exclusions, "skills": skills, "components": components,
        "inedible": [] if digestible else ["no-digestible-entrypoint"],
    }
    return record


def _skill_facts(path, data, files_in_skill, modes, skipped):
    text = data.decode("utf-8", "replace")
    fields, body = parse_frontmatter(text)
    name = fields.get("name", "")
    description = fields.get("description", "")
    fence_shell = re.search(r"(?im)^\s{0,3}(?:```|~~~)\s*(?:bash|sh|shell|zsh|console|powershell|pwsh|ps1|cmd|bat)\b", body)
    tools = [t.strip().split("(")[0].casefold() for t in re.split(r"[,\s]+", fields.get("allowed-tools", "")) if t.strip()]
    grants = sorted(t for t in tools if t and t not in READ_ONLY_TOOLS)
    skill_dir = str(PurePosixPath(path).parent)
    skill_dir = "" if skill_dir == "." else skill_dir
    blocked = []
    for member in files_in_skill:
        relative = member[len(skill_dir) + 1:] if skill_dir else member
        pure = PurePosixPath(relative)
        license_file = re.fullmatch(r"(?:license|licence|notice|copying)(?:\.[a-z]+)?", pure.name.casefold())
        metadata = relative.casefold() == "agents/openai.yaml"
        if ((pure.suffix.casefold() not in INSTALL_ALLOWED_SUFFIXES and not license_file and not metadata) or modes.get(member, "100644") != "100644"
                or member in skipped or pure.name.casefold() in ROUTER_NAMES
                or any(part.casefold() in (".claude", ".codex", ".agents", ".git", "hooks") for part in pure.parts[:-1])):
            blocked.append(member)
    return {"path": path, "dir": skill_dir, "name": sanitize_text(name, 64), "valid_name": bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)) and len(name) <= 64,
            "description_bytes": len(description.encode("utf-8")), "name_bytes": len(name.encode("utf-8")),
            "description_ok": bool(description.strip()) and len(description) <= 1024 and "<" not in description and ">" not in description,
            "body_bytes": len(body.encode("utf-8")), "inline_exec": bool(fence_shell), "tool_grants": grants,
            "outside_allowlist": blocked[:20], "outside_allowlist_count": len(blocked)}


def _split_components(files, roles, modes, flags, hooks, mcp, plugins, auto_exec, skipped):
    """Every food is split into reviewable parts with a kind and an execution class."""
    paths = sorted(files)
    assigned, components, ids = {}, [], set()

    def add(cid, kind, name, members, exec_class, where="", **extra):
        cid = re.sub(r"[^A-Za-z0-9:._/-]+", "-", cid)[:120]
        if cid in ids and where:
            cid = f"{cid}@{slug(where, 40)}"
        base, n = cid, 2
        while cid in ids:
            cid, n = f"{base}-{n}", n + 1
        ids.add(cid)
        members = sorted(set(members))
        for member in members:
            assigned.setdefault(member, cid)
        components.append({"id": cid, "kind": kind, "name": sanitize_text(name, 80), "paths": members,
                           "file_count": len(members), "bytes": sum(len(files[m]) for m in members if m in files),
                           "exec_class": exec_class, **extra})

    for config in sorted({h["path"] for h in hooks}):
        scripts = [p for p, source in auto_exec.items() if source == config]
        add("hooks:" + config, "hook-set", config, [config, *scripts], "X2",
            events=sorted({h["event"] for h in hooks if h["path"] == config}))
    for server in mcp:
        scripts = [p for p, source in auto_exec.items() if source == server["path"] and p not in assigned]
        add("mcp:" + server["name"], "mcp-server", server["name"], [server["path"], *scripts], "X2", remote=server["remote"])
    for plugin in plugins:
        if plugin["path"] not in assigned:
            add("plugin:" + plugin["path"], "plugin-manifest", plugin["path"], [plugin["path"]], "X2" if plugin["hooks"] or plugin["mcp"] else "X0",
                declares=plugin["declares"])
    for path, source in sorted(auto_exec.items()):
        if path not in assigned:
            add("exec:auto/" + path, "executable", path, [path], "X2")
    skill_files = sorted((p for p in paths if PurePosixPath(p).name.casefold() == "skill.md"), key=lambda p: -p.count("/"))
    owner_of = {}
    for skill in skill_files:
        parent = str(PurePosixPath(skill).parent)
        prefix = "" if parent == "." else parent + "/"
        for member in paths:
            if member.startswith(prefix) and member not in owner_of and member not in assigned:
                owner_of[member] = skill
    for skill in sorted(skill_files):
        members = [m for m, owner in owner_of.items() if owner == skill]
        facts = _skill_facts(skill, files[skill], members, modes, set(skipped))
        has_code = any(roles[m] in ("executable", "manifest", "binary") for m in members)
        exec_class = "X1" if has_code else ("X1-inline" if facts["inline_exec"] or facts["tool_grants"] else "X0")
        name = facts["name"] if facts["valid_name"] else (PurePosixPath(facts["dir"]).name or "root")
        add("skill:" + slug(name), "skill", name, members, exec_class, where=facts["dir"].rsplit("/", 2)[0] if facts["dir"] else "", skill=facts)
    rest = [p for p in paths if p not in assigned]
    groups = {}
    for path in rest:
        role, pure = roles[path], PurePosixPath(path)
        if role == "instruction" and pure.name.casefold() in ROUTER_NAMES:
            add("instructions:" + path, "instruction-file", path, [path], "X1-inline")
        elif role == "instruction":
            kind = "agent" if "agents" in [p.casefold() for p in pure.parts[:-1]] else "command"
            add(f"{kind}:{slug(pure.stem)}", kind, pure.stem, [path], "X0", where=str(pure.parent.parent))
        elif role == "manifest":
            groups.setdefault(("deps", "dependency-manifest", "dependency manifests", "X1"), []).append(path)
        elif role == "executable":
            top = pure.parts[0] if len(pure.parts) > 1 else "(root)"
            groups.setdefault((f"exec:{top}", "executable", f"scripts in {top}", "X1"), []).append(path)
        elif role == "binary":
            groups.setdefault(("binaries", "binary", "binary files", "X1"), []).append(path)
        elif role == "docs":
            groups.setdefault(("docs", "docs", "documentation", "X0"), []).append(path)
        else:
            groups.setdefault(("other", "other", "config, assets and other files", "X0"), []).append(path)
    for (cid, kind, name, exec_class), members in sorted(groups.items()):
        add(cid, kind, name, members, exec_class)
    return components


# --------------------------------------------------------------------------- derive

def evidence_class(record) -> str:
    """static, live, historical or ignored. Imported reports are always historical."""
    if not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION:
        return "ignored"
    if record.get("provenance") == "imported-report" or record.get("mode") == "historical-prior" or record.get("level") == "historical-prior":
        return "historical"
    if (record.get("provenance") == "deterministic" and record.get("mode") == "deterministic"
            and record.get("tier") == "T0" and record.get("level") == "static-measured"):
        return "static"
    if (record.get("provenance") in LIVE_PROVENANCE and record.get("mode") == "live" and record.get("level") == "measured"
            and _HEX64.fullmatch(str(record.get("bundle_sha256") or "")) and isinstance(record.get("consent_id"), str)
            and record["consent_id"]):
        return "live"
    return "ignored"


def _valid_decision(decision) -> bool:
    if not isinstance(decision, dict) or decision.get("kind") not in DECISION_KINDS:
        return False
    if decision["kind"] == "triage":
        return decision.get("outcome") in TRIAGE_OUTCOMES and isinstance(decision.get("flag"), str)
    return True


def _verdict(code, reasons, **extra):
    symbol, ascii_symbol, label, label_zh = VERDICTS[code]
    return {"headline": code, "symbol": symbol, "ascii": ascii_symbol, "label": label, "label_zh": label_zh,
            "reasons": list(reasons), **extra}


def propose_component(component: dict, open_flags: dict, license_info: dict) -> dict:
    """Proposed disposition and the reason; executable or flagged parts never default to absorb."""
    own = [open_flags[f] for f in component.get("flag_ids", []) if f in open_flags]
    high = [f for f in own if f["severity"] == "high"]
    medium = [f for f in own if f["severity"] == "medium"]
    kind = component["kind"]
    tx = "sandbox trial in a disposable environment (TX) - paid, not enabled in v0"

    def result(disposition, reason, missing="", owner_confirms=False, installable=False):
        return {"disposition": disposition, "reason": reason, "missing_test": missing,
                "owner_confirms": owner_confirms, "installable": installable}

    if high:
        refs = ", ".join(f"{f['rule']} {f['path']}:{f['line']}" for f in high[:3])
        return result("excrete", f"high-severity static flag(s): {refs}; static rules never mark toxic", owner_confirms=True)
    if kind == "skill":
        skill = component["skill"]
        if skill["body_bytes"] > LIMITS["skill_body_bytes"]:
            return result("hold", f"inedible as shipped: body {skill['body_bytes']} bytes > {LIMITS['skill_body_bytes']} (not harmful)",
                          "re-implement a smaller OAW skill, then T0 again")
        if not skill["valid_name"] or not skill.get("description_ok"):
            return result("hold", "SKILL.md lacks a valid lowercase name or a portable description", "fix structure, then T0 again")
        if component["exec_class"] != "X0":
            detail = "bundles scripts" if component["exec_class"] == "X1" else "instructs shell/tool actions"
            return result("hold", f"{component['exec_class']}: {detail}; never run on this machine", tx)
        if skill["outside_allowlist_count"]:
            return result("hold", f"{skill['outside_allowlist_count']} file(s) outside the install allowlist (.md/.txt, mode 644, no nested instructions)",
                          "re-implement without those files")
        if license_info.get("distribution") == "unknown":
            return result("hold", "license unknown: copying is not established", "owner license check")
        if medium:
            refs = ", ".join(f"{f['rule']} {f['path']}:{f['line']}" for f in medium[:3])
            return result("hold", f"open flag(s): {refs}", "owner triage of the flags")
        return result("absorb", "X0 text-only skill, no open flags, license " + str(license_info.get("spdx"))
                      + "; quality not measured, no improvement claimed", "", installable=True)
    if kind in ("hook-set", "mcp-server"):
        return result("hold", f"{kind} auto-executes (X2); OAW never installs hooks or MCP servers", tx)
    if kind == "plugin-manifest":
        return result("hold", "host plugin manifest; plugins are installed by the owner through the host, never by OAW", tx)
    if kind == "executable":
        return result("hold", "executable code; never run on this machine", tx)
    if kind == "dependency-manifest":
        return result("excrete", "package manifests conflict with OAW's stdlib-only runtime; nothing is installed", owner_confirms=True)
    if kind == "instruction-file":
        return result("excrete", "a second always-loaded instruction file conflicts with OAW's single AGENTS.md policy", owner_confirms=True)
    if kind in ("agent", "command"):
        return result("hold", f"{kind} prompt, not a native skill; needs re-implementation as an OAW skill",
                      "behavior A/B (paid), after re-implementation")
    if kind == "binary":
        return result("excrete", "binary files cannot be reviewed as text", owner_confirms=True)
    if kind == "docs":
        return result("hold", "reference material; never installed", "elephant proposal (method backlog)")
    return result("hold", "not digestible as shipped", "elephant proposal")


def derive(evidence, decisions=(), *, tier: str = "local") -> dict:
    """Food headline and per-component dispositions from evidence and owner decisions only.

    Imported reports and records without a consented live bundle are ignored, so
    they can never raise a verdict. Owner decisions can confirm toxicity,
    excrete parts or record absorption; they cannot raise a disposition.
    """
    static, live = [], []
    for record in evidence or ():
        kind = evidence_class(record)
        if kind == "static":
            static.append(record)
        elif kind == "live":
            live.append(record)
    decisions = [d for d in (decisions or ()) if _valid_decision(d)]
    triage = {d["flag"]: d["outcome"] for d in decisions if d["kind"] == "triage"}
    toxic_refs = sorted(flag for flag, outcome in triage.items() if outcome == "confirm-toxic")
    blocked = [d for d in decisions if d["kind"] in ("block", "reject")]
    base = {"tier": tier, "verdict_rules_version": VERDICT_RULES_VERSION, "chips": [], "badges": [], "stale": False}
    if not static:
        verdict = (_verdict("toxic", ["owner-confirmed: " + r for r in toxic_refs]) if toxic_refs
                   else _verdict("untested", ["no static record (taste not run)"]))
        return {**base, **verdict, "level": "not-measured", "safety": "toxic" if toxic_refs else "unknown",
                "exec_class": None, "allergens": [], "flags": {"total": 0, "open": 0, "open_high": 0, "triaged": 0},
                "components": [], "inputs": []}
    s = max(static, key=lambda r: (int(r.get("scanner_version") or 0), str(r.get("recorded_at") or ""), str(r.get("evidence_id"))))
    chips = []
    stale = int(s.get("scanner_version") or 0) < SCANNER_VERSION
    if stale:
        chips.append("rules-updated-free-T0-pending")
    all_flags = [f for f in s.get("flags", []) if isinstance(f, dict) and isinstance(f.get("id"), str)]
    open_flags = {f["id"]: f for f in all_flags if triage.get(f["id"]) not in ("benign", "allergen")}
    open_high = [f for f in open_flags.values() if f.get("severity") == "high"]
    inputs = [s.get("evidence_id")] + [r.get("evidence_id") for r in live]
    if toxic_refs:
        verdict = _verdict("toxic", ["owner-confirmed: " + r for r in toxic_refs])
        safety = "toxic"
    elif s.get("inedible"):
        verdict = _verdict("inedible", list(s["inedible"]), note="OAW cannot digest it; not a safety or quality verdict")
        safety = "flagged" if open_flags else "no-toxic-signal"
    elif open_high or blocked:
        reasons = [f"{len(open_high)} high-severity flag(s) not triaged"] if open_high else []
        reasons += [f"owner {d['kind']}: {sanitize_text(d.get('reason', ''), 80)}" for d in blocked]
        verdict, safety = _verdict("risky", reasons), "flagged"
    elif live:
        verdict, safety = _measured_verdict(live), "flagged" if open_flags else "no-toxic-signal"
    else:
        if not open_flags:
            chips.append("free-checks-passed")
        else:
            chips.append(f"open-flags:{len(open_flags)}")
        verdict = _verdict("untested", ["no measured evidence (paid tests not run)"])
        safety = "flagged" if open_flags else "no-toxic-signal"
    components = []
    component_decisions = {}
    for d in decisions:
        for cid in d.get("components") or ([d["component"]] if isinstance(d.get("component"), str) else []):
            component_decisions.setdefault(cid, []).append(d)
    for component in s.get("components", []):
        proposal = propose_component(component, open_flags, s.get("license") or {})
        if verdict["headline"] in ("toxic", "risky", "inedible") and proposal["disposition"] == "absorb":
            proposal.update(disposition="hold", reason=f"food is {verdict['headline']}; parts inherit it until resolved",
                            missing_test="owner triage", installable=False)
        decided = None
        for d in component_decisions.get(component["id"], []):
            if d["kind"] == "excrete":
                proposal.update(disposition="excrete", reason="owner excreted: " + sanitize_text(d.get("reason", ""), 120),
                                owner_confirms=False, installable=False)
                decided = "excreted"
            elif d["kind"] == "absorb" and proposal["disposition"] == "absorb" and decided != "excreted":
                decided = "absorbed"
            elif d["kind"] == "remove" and decided == "absorbed":
                decided = "removed"
        colour, label_zh = DISPOSITIONS[proposal["disposition"]]
        components.append({"id": component["id"], "kind": component["kind"], "name": component.get("name"),
                           "file_count": component.get("file_count"), "bytes": component.get("bytes"),
                           "exec_class": component.get("exec_class"), **proposal, "colour": colour, "label_zh": label_zh,
                           "level": "static-measured", "decision": decided,
                           "open_flags": [f for f in component.get("flag_ids", []) if f in open_flags]})
    return {**base, **verdict, "chips": chips + verdict.pop("chips", []), "stale": stale,
            "level": "measured" if live and verdict["headline"] not in ("toxic", "risky", "inedible") else "static-measured",
            "safety": safety, "exec_class": s.get("exec_class"), "allergens": list(s.get("allergens", [])),
            "flags": {"total": len(all_flags), "open": len(open_flags), "open_high": len(open_high),
                      "triaged": len(all_flags) - len(open_flags)},
            "components": components, "inputs": inputs}


def _measured_verdict(live) -> dict:
    """Minimal rules for consented live evidence (no v0 runner produces it yet)."""
    results = [r.get("result") for r in live]
    if any(r.get("result") == "regressed" and (r.get("deterministic") or r.get("confirmed")) for r in live):
        return _verdict("regressed", ["measured regression"])
    if "regressed" in results:
        return _verdict("incomplete", ["unconfirmed-negative: one cohort; not absorbable, not proven harmful"])
    if "incomplete" in results or any(r not in ("gain", "no-gain") for r in results):
        return _verdict("incomplete", ["measured evidence is incomplete"])
    if all(r == "no-gain" for r in results):
        return _verdict("no-gain", ["no gain observed under this specification"])
    gain = [r for r in live if r.get("result") == "gain"]
    if any(r.get("integration") == "diarrhea" and r.get("confirmed") for r in gain):
        return _verdict("diarrhea", ["harms the current recipe"])
    if not any(r.get("integration") == "clear" for r in gain):
        return _verdict("incomplete", ["integration-not-complete"])
    parity = {r.get("parity") for r in gain}
    if not parity & {"parity", "evolved"}:
        return _verdict("incomplete", ["parity-floor-not-run"])
    return _verdict("nutritious", ["measured gain with parity floor"], badges=["evolved"] if "evolved" in parity else [])


# --------------------------------------------------------------------------- builds and effect

def build_hash(file_hashes: dict) -> str:
    return tree_sha256(file_hashes)


def build_name(number: int, file_hashes: dict, release: str = RELEASE) -> str:
    """SemVer 2.0 build metadata: 2.0.0+build.N.<hash7>."""
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        raise ValueError("Build numbers start at 1.")
    name = f"{release}+build.{number}.{build_hash(file_hashes)[:7]}"
    parse_build_name(name)
    return name


def parse_build_name(name: str) -> dict:
    match = re.fullmatch(r"((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))\+build\.((?:0|[1-9]\d*))\.([0-9a-f]{7})", str(name))
    if not match:
        raise ValueError(f"Not a SemVer 2.0 OAW build name: {sanitize_text(name, 80)!r}")
    return {"release": match.group(1), "number": int(match.group(2)), "hash7": match.group(3)}


_SKILL_PATH = re.compile(r"\.(agents|claude)/skills/([^/]+)/SKILL\.md")
_HOST_SETTING_PATHS = (".claude/settings.json", ".claude/settings.local.json", ".codex/config.toml", ".codex/hooks.json", ".mcp.json")


def install_inventory(files: dict) -> dict:
    """Static inventory of an OAW install layer given {relative path: bytes}."""
    skills, startup, hooks, deps = {}, {"codex": 0, "claude": 0}, 0, set()
    local_modules = {PurePosixPath(p).stem.casefold().replace("_", "-") for p in files if p.endswith(".py")}
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    agents_md = len(files.get("AGENTS.md", b""))
    claude_md = files.get("CLAUDE.md", b"")
    startup["codex"] += agents_md
    startup["claude"] += len(claude_md) + (agents_md if re.search(rb"(?m)(?:^|\s)@(?:\./)?AGENTS\.md", claude_md) else 0)
    for path, data in sorted(files.items()):
        match = _SKILL_PATH.fullmatch(path)
        if match:
            host = "codex" if match.group(1) == "agents" else "claude"
            fields, _body = parse_frontmatter(data.decode("utf-8", "replace"))
            meta = len(fields.get("name", "").encode()) + len(fields.get("description", "").encode())
            entry = skills.setdefault(match.group(2), {"hosts": [], "metadata_bytes": meta})
            entry["hosts"].append(host)
            startup[host] += meta
        elif re.fullmatch(r"\.claude/agents/[^/]+\.md", path):
            fields, _body = parse_frontmatter(data.decode("utf-8", "replace"))
            startup["claude"] += len(fields.get("name", "").encode()) + len(fields.get("description", "").encode())
        name = PurePosixPath(path).name.casefold()
        if name.endswith(".json") and (name == "hooks.json" or path in _HOST_SETTING_PATHS):
            config = _json(data)
            if config:
                hooks += sum(1 for _ in _hook_commands(config))
        if path.endswith(".py"):
            deps |= {m for m in _code_imports(path, data.decode("utf-8", "replace"))
                     if m.replace("-", "_") not in stdlib and m not in local_modules and m != "__future__"}
        elif PurePosixPath(path).name.casefold() in ("package.json", "requirements.txt", "pyproject.toml"):
            deps |= {d for d, _spec in _declared_deps(path, data)}
    return {"skills": {k: {"hosts": sorted(v["hosts"]), "metadata_bytes": v["metadata_bytes"]} for k, v in sorted(skills.items())},
            "files": len(files), "bytes": sum(len(v) for v in files.values()),
            "startup_bytes": {"AGENTS.md": agents_md, "CLAUDE.md": len(claude_md), "by_host": startup},
            "hooks": hooks, "non_stdlib_deps": sorted(deps),
            "host_settings_writes": sorted(p for p in files if p in _HOST_SETTING_PATHS)}


def effect_vs_default(current: dict, default: dict, measured=()) -> dict:
    """Effect of this build versus the default release. Quality is not measured without live evidence."""
    lines = []

    def line(metric, now, base, level="static-measured", note=""):
        delta = now - base if isinstance(now, int) and isinstance(base, int) else None
        lines.append({"metric": metric, "current": now, "default": base, "delta": delta, "level": level, "note": note})

    added = sorted(set(current["skills"]) - set(default["skills"]))
    removed = sorted(set(default["skills"]) - set(current["skills"]))
    line("skills", len(current["skills"]), len(default["skills"]), note=f"added {len(added)}, removed {len(removed)}")
    line("files", current["files"], default["files"])
    line("bytes", current["bytes"], default["bytes"])
    for host in ("codex", "claude"):
        line(f"startup-loaded text bytes ({host})", current["startup_bytes"]["by_host"][host], default["startup_bytes"]["by_host"][host],
             note="AGENTS.md/CLAUDE.md plus every SKILL.md name+description; bytes/4 is only a token estimate")
    line("hooks", current["hooks"], default["hooks"])
    line("non-stdlib dependencies", len(current["non_stdlib_deps"]), len(default["non_stdlib_deps"]),
         note=", ".join(current["non_stdlib_deps"]) or "none")
    line("host settings writes", len(current["host_settings_writes"]), len(default["host_settings_writes"]),
         note=", ".join(current["host_settings_writes"]) or "none")
    live = [r for r in measured or () if evidence_class(r) == "live"]
    if live:
        verdict = _measured_verdict(live)
        quality = {"metric": "quality", "value": verdict["label"], "level": "measured",
                   "note": "enhanced" if verdict["headline"] == "nutritious" else "no improvement claimed"}
    else:
        quality = {"metric": "quality", "value": "not measured", "level": "not-measured",
                   "note": "no consented live comparison; never shown as enhanced"}
    quality.update(current=None, default=None, delta=None)
    lines.append(quality)
    return {"release": RELEASE, "skills": {"added": added, "removed": removed,
                                           "same": sorted(set(current["skills"]) & set(default["skills"]))},
            "lines": lines, "quality": quality}


# --------------------------------------------------------------------------- policy and plans

def validate_policy(per_food_tokens, weekly_tokens, sandbox) -> dict:
    if not all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 10**10 for v in (per_food_tokens, weekly_tokens)):
        raise ValueError("Token caps must be whole numbers between 0 and 10^10.")
    if weekly_tokens < per_food_tokens:
        raise ValueError("The weekly cap must be at least the per-food cap.")
    conditions = sorted(set(sandbox))
    unknown = [c for c in conditions if c not in SANDBOX_CONDITIONS]
    if unknown or not conditions:
        raise ValueError("Sandbox conditions must be a nonempty subset of: " + ", ".join(SANDBOX_CONDITIONS))
    return {"schema_version": SCHEMA_VERSION, "per_food_token_cap": per_food_tokens, "weekly_token_cap": weekly_tokens,
            "sandbox": conditions, "paid_runs_enabled": False}


def _tokens(runs):
    return {"runs": runs, "min": runs * TOKENS_PER_RUN[0], "max": runs * TOKENS_PER_RUN[1], "label": TOKEN_LABEL}


def decide_plan(food: str, derived: dict, historical=(), policy: dict | None = None) -> dict:
    """D11: the system picks the food's tests from its evidence, cheapest first."""
    components = derived.get("components", [])
    has_static = bool(derived.get("inputs"))
    executable = [c for c in components if c["disposition"] == "hold" and c["exec_class"] in ("X1", "X1-inline", "X2")]
    candidates = [c for c in components if c["disposition"] == "absorb" or (c["disposition"] == "hold" and c["kind"] in ("skill", "agent", "command"))]
    methods = [c for record in historical for c in record.get("components", []) if c.get("disposition") in ("absorb", "hold")]
    steps = [{"id": "T0", "name": "static checks", "cost": "free", "state": "done" if has_static else "next",
              "can_prove": ["file inventory, license, declared hooks/MCP/scripts, flags"],
              "cannot_prove": ["behavior, quality, runtime safety"], "tokens": None}]
    steps.append({"id": "T1", "name": "offline fit (name collisions, doctor/migrate round trip)", "cost": "free",
                  "state": "not available in v0", "can_prove": ["install compatibility"], "cannot_prove": ["quality"], "tokens": None})
    headline = derived.get("headline")
    status, basis = None, []
    if headline == "toxic":
        status, basis = "no paid test: owner confirmed toxic", ["toxic is final until new evidence and owner review"]
    elif headline == "inedible":
        status, basis = "no paid test: OAW cannot digest this food as shipped", list(derived.get("reasons", []))
    elif headline == "risky":
        steps.append({"id": "T2a", "name": "owner triage of high-severity flags", "cost": "free (owner time)", "state": "next",
                      "can_prove": ["whether each flag is benign, an allergen or toxic"], "cannot_prove": ["quality"], "tokens": None})
        status, basis = "blocked: high-severity flags must be triaged before any paid test", list(derived.get("reasons", []))
    elif not has_static:
        status, basis = "taste first: free static checks decide the paid plan", ["no static record"]
    elif not candidates and not methods:
        status, basis = "no paid test needed: nothing absorbable", ["every component is excreted or reference-only"]
    if status is None:
        if methods or candidates:
            steps.append({"id": "G", "name": "goldfish blind review of the absorption drafts (2 reviewers)", "cost": "paid",
                          "state": "planned", "can_prove": ["unsupported claims or rule conflicts in our drafts"],
                          "cannot_prove": ["behavior gain"], "tokens": _tokens(2)})
        if executable:
            steps.append({"id": "TX", "name": f"sandbox trial of {len(executable)} executable part(s) in a disposable environment",
                          "cost": "paid", "state": "planned", "can_prove": ["tripwires: writes, network, processes outside the declared scope"],
                          "cannot_prove": ["quality"], "tokens": _tokens(2 * len(executable))})
        if candidates or methods:
            steps.append({"id": "T3a-smoke", "name": "behavior A/B smoke: with the food (C) vs without (D), 4 cases x 2 runs",
                          "cost": "paid", "state": "planned", "can_prove": ["deterministic regressions; early no-gain signal"],
                          "cannot_prove": ["statistical gain", "other hosts or models"], "tokens": _tokens(16)})
            steps.append({"id": "T4", "name": "integration with the current recipe (victim checks)", "cost": "paid", "state": "planned",
                          "can_prove": ["diarrhea: harm to existing skills"], "cannot_prove": ["gain"], "tokens": _tokens(16)})
            steps.append({"id": "P", "name": "parity floor: OAW with the food (C) vs the food alone (B)", "cost": "paid",
                          "state": "planned", "can_prove": ["parity or evolution claim"], "cannot_prove": ["other hosts"], "tokens": _tokens(16)})
            steps.append({"id": "T3a", "name": "behavior A/B full: 8 cases x 5 runs per arm", "cost": "paid",
                          "state": "only if the smoke shows no deterministic negative",
                          "can_prove": ["calibrated gain or regression on this suite"], "cannot_prove": ["other tasks, long-term effects"],
                          "tokens": _tokens(80)})
        basis = [f"{len(candidates)} absorbable or skill-type part(s)", f"{len(methods)} historical method proposal(s)",
                 f"{len(executable)} executable part(s) on hold"]
    paid = [s for s in steps if s["tokens"]]
    paid.sort(key=lambda s: s["tokens"]["max"])
    free = [s for s in steps if not s["tokens"]]
    total = {"min": sum(s["tokens"]["min"] for s in paid), "max": sum(s["tokens"]["max"] for s in paid), "label": TOKEN_LABEL}
    if status is None:
        if not policy:
            status = "waiting for standing policy"
        elif total["max"] <= policy.get("per_food_token_cap", -1):
            status = "within policy - paid runs not enabled in v0"
        else:
            status = "exceeds standing policy - owner approval needed (paid runs not enabled in v0)"
    plan = {"schema_version": SCHEMA_VERSION, "food": food, "decided_by": "system (D11), from evidence; owner sets only the standing policy",
            "headline": headline, "basis": basis, "steps": free + paid, "estimate": total, "status": status,
            "paid_runs_enabled": False, "policy_sha256": record_sha256(policy) if policy else None}
    plan["plan_id"] = "p-" + record_sha256({k: v for k, v in plan.items() if k != "policy_sha256"})[:12]
    return plan


# --------------------------------------------------------------------------- scout relevance

_STRONG = ("claude code", "claude-code", "claudecode", "codex", "coding agent", "coding-agent", "agent skill", "agent-skill",
           "agentskills", "skill.md", "claude skill", "subagent", "agent harness", "harness", "mcp server", "model context protocol",
           "agents.md", "claude.md", "agentic coding", "ai coding", "cursor rules", "slash command", "claude-plugin")
_UNRELATED = ("video", "youtube", "tiktok", "image generation", "stable diffusion", "comfyui", "music", "audio", "podcast",
              "trading", "crypto", "stock", "wallpaper", "anime", "minecraft", "photo", "voice clone", "text-to-speech",
              "subtitle", "movie", "ebook", "resume")


def relevance(item: dict) -> dict:
    """D4 filter: keep only coding-agent skill/harness repos; stars are not consulted."""
    text = _normalized(" ".join([str(item.get("full_name") or item.get("name") or ""), str(item.get("description") or ""),
                                 " ".join(str(t) for t in item.get("topics") or [])]).replace("_", " "))
    strong = [term for term in _STRONG if term in text]
    unrelated = [term for term in _UNRELATED if re.search(r"\b" + re.escape(term) + r"s?\b", text)]
    if not strong:
        return {"keep": False, "reason": "no coding-agent skill or harness signal"}
    if unrelated and len(strong) < 2:
        return {"keep": False, "reason": f"unrelated domain: {unrelated[0]}"}
    return {"keep": True, "reason": "signals: " + ", ".join(strong[:4])}


# --------------------------------------------------------------------------- imported reports

def _count(values) -> dict:
    counts = {}
    for value in values:
        key = sanitize_text(value, 30) or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def imported_record(food: str, docs: dict, source_files: list, recorded_at: str) -> dict:
    """Historical-prior evidence from an Elephant/Goldfish digestion directory.

    Whatever the files claim, the record is `imported-report` / `historical-prior`:
    `derive()` ignores it, so it can be shown but never raise a verdict.
    """
    digest = docs.get("digest.json") if isinstance(docs.get("digest.json"), dict) else None
    verify = docs.get("verify.json") if isinstance(docs.get("verify.json"), dict) else None
    ledger = docs.get("components.json") if isinstance(docs.get("components.json"), dict) else None
    scout = docs.get("scout.json") if isinstance(docs.get("scout.json"), dict) else {}
    integration = docs.get("integration.json") if isinstance(docs.get("integration.json"), dict) else None
    proposals = docs.get("proposals.md") if isinstance(docs.get("proposals.md"), str) else None
    lists = lambda doc, key: [x for x in doc.get(key, []) if isinstance(x, dict)] if isinstance(doc.get(key), list) else []
    elephant = None
    if digest:
        elephant = {"integration_mode": sanitize_text(digest.get("integration_mode"), 60),
                    "what_it_does": sanitize_text(digest.get("what_it_does"), 400),
                    "gates": [{"gate": sanitize_text(g.get("gate"), 60), "verdict": sanitize_text(g.get("verdict"), 20)} for g in lists(digest, "gates")[:40]],
                    "nutrients": len(lists(digest, "nutrients")), "diarrhea_risks": len(lists(digest, "diarrhea_risks")),
                    "proposed_ab_tests": len(lists(digest, "proposed_ab_tests"))}
    verified = None
    if verify:
        verified = {"checks": len(lists(verify, "checks")), "by_status": _count(c.get("status") for c in lists(verify, "checks")),
                    "missed_issues": len(lists(verify, "missed_issues")),
                    "integration_mode_agrees": verify.get("integration_mode_agrees") if isinstance(verify.get("integration_mode_agrees"), bool) else None}
    goldfish = []
    for name in sorted(n for n in docs if n.startswith("goldfish-") and isinstance(docs[n], dict)):
        doc = docs[name]
        findings = lists(doc, "findings")
        goldfish.append({"reviewer": sanitize_text(doc.get("reviewer") or name[:-5], 40), "file": name, "findings": len(findings),
                         "by_severity": _count(f.get("severity") for f in findings),
                         "summary": sanitize_text(doc.get("verdict_summary"), 300)})
    components = []
    for item in lists(ledger or {}, "components")[:300]:
        raw = str(item.get("id") or "")
        cid = "hist:" + re.sub(r"[^A-Za-z0-9._-]+", "-", raw)[:80] if raw else "hist:" + sha256_bytes(canonical_json(item).encode())[:8]
        disposition = item.get("disposition") if item.get("disposition") in DISPOSITIONS else "hold"
        components.append({"id": cid, "kind": "method", "name": sanitize_text(item.get("name"), 120), "disposition": disposition,
                           "proposed_by": "elephant (historical-prior)", "oaw_target": sanitize_text(item.get("oaw_target"), 200),
                           "reason": sanitize_text(item.get("reason"), 300), "missing_test": sanitize_text(item.get("missing_test"), 200),
                           "level": "historical-prior"})
    integration_summary = None
    if integration:
        integration_summary = {sanitize_text(k, 40): (sanitize_text(v, 160) if isinstance(v, (str, int, float, bool)) else f"{len(v)} item(s)")
                               for k, v in list(integration.items())[:20] if isinstance(v, (str, int, float, bool, list, dict))}
    commit = next((c for c in ((ledger or {}).get("pinned_commit"), scout.get("commit")) if isinstance(c, str) and re.fullmatch(r"[0-9a-f]{40}", c)), None)
    files_sha = record_sha256(sorted((f["name"], f["sha256"]) for f in source_files))
    return {"schema_version": SCHEMA_VERSION, "evidence_id": f"{food}/imported/{files_sha[:12]}", "food": food,
            "tier": "imported", "mode": "historical-prior", "provenance": "imported-report", "level": "historical-prior",
            "pinned_commit": commit, "source_files": source_files, "elephant": elephant, "verify": verified, "goldfish": goldfish,
            "components": components, "counts": {k: sum(1 for c in components if c["disposition"] == k) for k in DISPOSITIONS},
            "integration": integration_summary,
            "proposals": {"bytes": len(proposals.encode("utf-8")),
                          "headings": [sanitize_text(h, 120) for h in re.findall(r"(?m)^#{1,3}\s+(.+)$", proposals)[:40]]} if proposals else None,
            "note": "imported report: historical-prior, shown separately, never counted in a verdict", "recorded_at": recorded_at}


# --------------------------------------------------------------------------- view model

def historical_summary(record: dict) -> dict:
    """Display-only digest of an imported report; values are already sanitized."""
    return {"level": "historical-prior", "note": "imported report; not counted in any verdict",
            "evidence_id": record.get("evidence_id"), "source_files": record.get("source_files", []),
            "elephant": record.get("elephant"), "verify": record.get("verify"), "goldfish": record.get("goldfish", []),
            "components": record.get("components", []), "counts": record.get("counts", {}),
            "integration": record.get("integration"), "proposals": record.get("proposals")}


def _steps(entry, derived, plan, has_static):
    paid_note = plan["status"] if plan else "waiting for standing policy"
    return [
        {"step": "found", "label_zh": "找到", "state": "done", "summary": entry.get("origin", "url")},
        {"step": "taste", "label_zh": "試吃（免費）", "state": "done" if has_static else "todo", "free": True,
         "summary": (f"{derived['flags']['total']} flag(s), {derived['flags']['open_high']} high open" if has_static else "not tasted")},
        {"step": "measure", "label_zh": "實測（付費，依常設預算）", "state": "measured" if derived.get("level") == "measured" else "not-run",
         "paid": True, "summary": paid_note},
        {"step": "result", "label_zh": "結果", "state": "done" if has_static else "pending",
         "summary": f"{derived['symbol']} {derived['label']}"},
    ]


def food_card(entry: dict, evidence: list, decisions: list, plan: dict | None = None) -> dict:
    derived = derive(evidence, decisions)
    backlog = {cid for d in decisions if d.get("kind") == "absorb" and d.get("outcome") == "backlog" for cid in d.get("components") or []}
    historical = []
    for record in evidence:
        if evidence_class(record) == "historical":
            summary = historical_summary(record)
            summary["components"] = [{**c, "decision": "absorbed as backlog item" if c.get("id") in backlog else None}
                                     for c in summary["components"]]
            historical.append(summary)
    static = [r for r in evidence if evidence_class(r) == "static"]
    s = max(static, key=lambda r: (int(r.get("scanner_version") or 0), str(r.get("recorded_at") or ""))) if static else None
    counts = {k: sum(1 for c in derived["components"] if c["disposition"] == k) for k in DISPOSITIONS}
    source = entry.get("source", {})
    private = source.get("kind") == "file"
    display = sanitize_text(entry.get("display") or entry.get("id"), 80)
    safety_text = ("owner-confirmed toxic" if derived["safety"] == "toxic" else
                   f"no toxic signal observed ({s['counts']['files']} files, {len(s['checks_run'])} checks, {s['tree_sha256'][:12]})" if s and derived["safety"] != "flagged" else
                   f"{derived['flags']['open']} open flag(s), {derived['flags']['open_high']} high" if s else "not checked")
    food_decisions = [{"at": d.get("at"), "kind": d.get("kind"), "components": d.get("components") or [], "outcome": d.get("outcome"),
                       "reason": sanitize_text(d.get("reason", ""), 160), "build": d.get("build")} for d in decisions]
    return {"id": entry["id"], "display": display, "repo": None if private else source.get("url"), "origin": entry.get("origin"),
            "lifecycle": entry.get("lifecycle"),
            "pinned": {"commit": source.get("commit"), "commit7": (source.get("commit") or "")[:7] or None,
                       "integrity": source.get("integrity"), "tree_sha12": (s or {}).get("tree_sha256", "")[:12] or None},
            "steps": _steps(entry, derived, plan, bool(s)),
            "verdict": {k: derived[k] for k in ("headline", "symbol", "ascii", "label", "label_zh", "reasons", "chips", "badges", "level", "stale")},
            "safety_text": safety_text, "exec_class": derived["exec_class"], "allergens": derived["allergens"],
            "flags": derived["flags"], "license": (s or {}).get("license", {}).get("spdx") if s else None,
            "components": derived["components"], "counts": counts, "historical": historical,
            "plan": {"status": plan["status"], "plan_id": plan["plan_id"], "estimate": plan["estimate"]} if plan else None,
            "decisions": food_decisions}


def build_view(state: dict) -> dict:
    """The only view model renderers read. Derived, never hand-edited."""
    registry = state.get("registry") or {"foods": {}}
    evidence = state.get("evidence") or {}
    decisions = state.get("decisions") or []
    plans = state.get("plans") or {}
    builds = state.get("builds") or {"builds": [], "current": None}
    policy = state.get("policy")
    scout = state.get("scout") or {"candidates": {}}
    receipts = state.get("receipts") or {}
    foods = []
    for fid, entry in sorted(registry.get("foods", {}).items()):
        mine = [d for d in decisions if d.get("food") == fid]
        card = food_card(entry, evidence.get(fid, []), mine, plans.get(fid))
        present = (receipts.get(fid) or {}).get("components") or {}
        for part in card["components"]:
            part["in_current_build"] = part["id"] in present
        for report in card["historical"]:
            for part in report["components"]:
                part["in_current_build"] = part["id"] in present
        foods.append(card)
    candidates = sorted(scout.get("candidates", {}).values(), key=lambda c: (-int(c.get("stars") or 0), c.get("key", "")))
    timeline = [{"n": b.get("n"), "name": b.get("name"), "label": sanitize_text(b.get("label", ""), 160), "kind": b.get("kind"),
                 "created_at": b.get("created_at"), "skills": b.get("skills", []), "components": b.get("components", []),
                 "change": b.get("change", {}), "effect": b.get("effect"), "doctor": b.get("doctor"),
                 "current": b.get("name") == builds.get("current"), "restore": f"catalog.py restore {b.get('name')}"}
                for b in builds.get("builds", [])]
    funnel = {"submitted": len(foods), "tasted": sum(1 for f in foods if f["steps"][1]["state"] == "done"),
              "measured": sum(1 for f in foods if f["verdict"]["level"] == "measured"),
              "absorbed_parts": sum(1 for f in foods for c in f["components"] if c["decision"] == "absorbed")
              + sum(1 for f in foods for d in f["decisions"] if d["kind"] == "absorb" and d["outcome"] == "backlog")}
    view = {
        "schema": VIEW_SCHEMA, "release": RELEASE,
        "generated_from": {name: record_sha256(state.get(name)) for name in ("registry", "evidence", "decisions", "builds", "policy", "scout", "plans", "effect", "receipts")},
        "vocabulary": {"verdicts": {k: {"symbol": v[0], "ascii": v[1], "label": v[2], "label_zh": v[3]} for k, v in VERDICTS.items()},
                       "dispositions": {k: {"colour": v[0], "label_zh": v[1]} for k, v in DISPOSITIONS.items()},
                       "evidence_levels": EVIDENCE_LEVELS},
        "my_oaw": {"release": RELEASE, "current_build": builds.get("current"),
                   "current_matches_build": state.get("current_matches_build"),
                   "timeline": timeline, "effect": state.get("effect")},
        "feeding": {"add": "catalog.py add URL [URL ...]",
                    "scout": {"order_basis": "queue order only (stars), not quality",
                              "last_run": (scout.get("runs") or [None])[-1],
                              "dropped_without_review": int(scout.get("dropped_total", 0)),
                              "candidates": [{"rank": i + 1, "key": c.get("key"), "display": sanitize_text(c.get("display"), 80),
                                              "description": sanitize_text(c.get("description"), 160), "stars": c.get("stars"),
                                              "relevance": c.get("relevance"), "status": c.get("status", "candidate"),
                                              "weeks_seen": c.get("weeks_seen", [])} for i, c in enumerate(candidates)]}},
        "foods": foods, "funnel": funnel,
        "policy": {"set": bool(policy), **({k: policy[k] for k in ("per_food_token_cap", "weekly_token_cap", "sandbox", "set_at") if k in policy} if policy else {}),
                   "paid_runs_enabled": False, "note": "v0 shows plans and estimates only; paid runs are not implemented"},
        "honesty": ["No evidence, no verdict; stars only order the scout queue.",
                    "Food bytes stay sealed outside the project and are never executed.",
                    "Static rules raise flags only; toxic needs owner confirmation.",
                    "Imported reports are historical-prior and never counted in a verdict.",
                    "Quality is 'not measured' unless consented live evidence exists; never 'enhanced' without it.",
                    "While running, only progress and spend are shown, never interim scores."],
    }
    return view
