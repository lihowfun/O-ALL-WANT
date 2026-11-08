#!/usr/bin/env python3
"""Pick a working mode (light, standard or deep) from a change, list its review steps, and keep the EGM switch.

Light is the default. `suggest` applies fixed rules to a git diff or a path list:

  deep      harness or infrastructure that runs on every session, an
            irreversible-looking change, or a new design or plan document
  standard  a code change of 300+ lines or 10+ files with no deep trigger
  light     everything else, including docs-only and small changes

Run it before a change (`--paths` with the files you plan to touch) and after
it (the working tree, or `--range`). Its `steps` say what to do and when:
deep plans first and gets a design review before any code, chosen by the
project's EGM switch; standard and deep get a fresh-context code review.

`egm on|auto|off` sets the switch in .oaw/settings.json (auto, the default,
uses the best-evidenced design review: one fresh-context review until the
X2 study decides; on runs full EGM). `reviewed` records a
finished design review so it is not run twice for the same file content.
`show MODE` prints the host commands for that mode.

Part of OAW. https://github.com/lihowfun/O-ALL-WANT
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePath, PurePosixPath
import posixpath
import re
import shlex
import subprocess
import sys
import tempfile

MODES = ("light", "standard", "deep")
# Size threshold for standard: non-documentation files only (added + deleted lines).
STANDARD_LINES = 300
STANDARD_FILES = 10
# More deleted files than this looks irreversible.
DEEP_DELETED_FILES = 5
DOC_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ".adoc"}
POLICY_NAMES = {"AGENTS.md", "CLAUDE.md"}
# OAW and harness scripts that run on every session or gate every change.
HARNESS_SCRIPTS = {"oaw.py", "harness_check.py", "sync_examples.py", "sync_egm.py", "validate_skills.py",
                   "context_hub.py", "oaw_common.py", "oaw_mode.py", "wiki_sync.py", "improvement.py"}
HOOK_PREFIXES = (".claude/hooks/", ".codex/", ".githooks/", ".husky/")
# install*, setup* or bootstrap* with a script extension: install.sh, setup_env.sh, installDeps.py.
INSTALLER = re.compile(r"(?i)^(?:install|setup|bootstrap)[^/]*\.(?:sh|ps1|bat|cmd|py)$")
UNTRACKED_LINE_LIMIT = 1_000_000  # bytes; larger untracked files count as files without line counts
SUGGEST_EXAMPLES = "Examples: --range main..HEAD, --paths docs/a.md scripts/b.py"
# Added in 2.0.1 and not yet checked against outcomes (unlike the V7-checked triggers): new plan or decision docs.
PLAN_DIRS = ("docs/plans/", "docs/adr/", "docs/adrs/", "docs/rfc/", "docs/rfcs/")
PLAN_NAME = re.compile(r"(?:^|[-_.])plan\.md$")
# Tool runtimes, installed skills and vendored code hold design-like file names that are not this project's designs
# (an uncommitted OAW install adds the EGM runtime's design_doc.md, for example).
NOT_PROJECT_DOCS = (".oaw/", ".claude/", ".agents/", ".codex/", "vendor/", "third_party/", "node_modules/")

# The EGM switch (owner decision D33). "auto" uses the design review with the best evidence; update both
# lines together when new evidence (the 2.0.1 X2 study) ranks another review higher. Owner decision D37
# (2026-11-09) moved auto from EGM to one fresh-context review until X2 decides.
SETTINGS_FILE = ".oaw/settings.json"
EGM_SWITCH = ("on", "auto", "off")
AUTO_DESIGN_REVIEW = "fresh-context"
AUTO_BASIS = ("until the X2 study decides (owner decision D37): EGM's measured gain (3/3 planted plan defects "
              "versus native 1/6, OAW validation 2026-11-07) rests on one selected case and costs about 28x a native "
              "review; for full EGM, run python3 scripts/oaw_mode.py egm on")
DEFAULT_EGM_MAX_TOKENS = 25_000_000
SECOND_OPINIONS = ("same", "codex", "claude")
DEFAULTS = {"egm": "auto", "egm_max_tokens": DEFAULT_EGM_MAX_TOKENS, "second_opinion": "same", "dry_run": False}
REVIEWS_DIR = ".oaw/reviews"
# Rough EGM cost from the bytes it reads (target plus context), fitted to two measured runs with Opus 5.5:
# about 2.3 KB -> 1.1M tokens in 8 minutes, about 105 KB -> 18.5M tokens in 31 minutes. Mostly cache reads.
EGM_TOKENS_BASE, EGM_TOKENS_PER_KB = 710_000, 169_000
EGM_MINUTES_BASE, EGM_MINUTES_PER_KB = 7.9, 0.22
# Even a tiny plan starts six or more reviewer subagents: the measured small runs used 1.07M-1.43M tokens.
EGM_TOKENS_FLOOR, EGM_MINUTES_FLOOR = 1_000_000, 7
ESTIMATE_LOW, ESTIMATE_HIGH = 0.8, 1.6
REVIEW_NAMES = {"egm": "EGM", "fresh-context": "one fresh-context reviewer", "none": "none"}


class ModeError(Exception):
    """A handled failure printed without a traceback."""


def git(root: Path, *args: str) -> bytes:
    command = ["git", "-C", str(root), "-c", "core.quotepath=false", *args]
    try:
        process = subprocess.run(command, input=b"", capture_output=True, check=False)
    except OSError as exc:
        raise ModeError(f"git is not available: {exc}") from exc
    if process.returncode:
        message = process.stderr.decode("utf-8", "replace").strip().splitlines()
        raise ModeError(f"git {' '.join(args[:2])} failed: {message[-1] if message else 'exit ' + str(process.returncode)}")
    return process.stdout


def project_root(value: str | None) -> Path:
    """The project to inspect: --root, else the folder that holds this script's scripts/ folder."""
    root = Path(value).resolve() if value else Path(__file__).resolve().parents[1]
    if not root.is_dir():
        raise ModeError(f"root is not a directory: {value}")
    return root


def split_z(data: bytes) -> list[str]:
    return [item.decode("utf-8", "surrogateescape") for item in data.split(b"\0")]


def parse_name_status(data: bytes) -> dict[str, dict]:
    """Parse `git diff --name-status -z`; a rename or copy keeps its source path."""
    tokens, entries, index = split_z(data), {}, 0
    while index < len(tokens) and tokens[index]:
        status = tokens[index][:1]
        if status in ("R", "C"):
            old, path = tokens[index + 1], tokens[index + 2]
            index += 3
        else:
            old, path = None, tokens[index + 1]
            index += 2
        entries[path] = {"path": path, "status": status, "old_path": old, "lines": 0, "lines_known": True}
    return entries


def parse_numstat(data: bytes) -> dict[str, int | None]:
    """Parse `git diff --numstat -z`: changed lines per path, None for binary files."""
    tokens, counts, index = split_z(data), {}, 0
    while index < len(tokens) and tokens[index]:
        added, deleted, path = tokens[index].split("\t", 2)
        index += 1
        if not path:  # rename or copy: the old and new paths follow
            path = tokens[index + 1]
            index += 2
        counts[path] = None if added == "-" else int(added) + int(deleted)
    return counts


def count_lines(path: Path) -> int | None:
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > UNTRACKED_LINE_LIMIT:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8000]:
        return None
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def diff_entries(root: Path, revision_range: str | None) -> tuple[list[dict], str]:
    if revision_range is not None:
        if revision_range.startswith("-") or ".." not in revision_range:
            raise ModeError("--range must look like A..B or A...B")
        spec, source = [revision_range], f"git diff {revision_range}"
    else:
        try:
            git(root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}")
            spec = ["HEAD"]
        except ModeError:  # no commit yet: compare with the empty tree
            spec = [git(root, "hash-object", "-t", "tree", "--stdin").decode().strip()]
        source = "working tree against HEAD"
    # --relative keeps a sub-project root to its own files, with root-relative paths;
    # ls-files run from the root lists only untracked files below it, relative to it.
    options = ["--relative", "--no-ext-diff", "--no-textconv", "--find-renames", "-z"]
    entries = parse_name_status(git(root, "diff", "--name-status", *options, *spec, "--"))
    for path, lines in parse_numstat(git(root, "diff", "--numstat", *options, *spec, "--")).items():
        if path in entries:
            entries[path]["lines"] = lines or 0
            entries[path]["lines_known"] = lines is not None
    if revision_range is None:
        for path in split_z(git(root, "ls-files", "--others", "--exclude-standard", "-z")):
            if path and path not in entries:
                lines = count_lines(root / path)
                entries[path] = {"path": path, "status": "A", "old_path": None,
                                 "lines": lines or 0, "lines_known": lines is not None}
    return sorted(entries.values(), key=lambda entry: entry["path"]), source


def in_git(root: Path) -> bool:
    try:
        git(root, "rev-parse", "--git-dir")
    except ModeError:
        return False
    return True


def head_files(root: Path, paths: list[str]) -> set[str] | None:
    """Which of these project-relative paths HEAD has; None outside a git repository."""
    try:
        git(root, "rev-parse", "--git-dir")
    except ModeError:
        return None
    try:
        git(root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}")
    except ModeError:
        return set()  # no commit yet: everything is new
    return set(split_z(git(root, "ls-tree", "-r", "-z", "--name-only", "HEAD", "--", *paths))) - {""}


def project_relative(root: Path, raw: str) -> str:
    """One spelling for a project path: relative, forward slashes, no ./ (an absolute path inside the project too)."""
    value = raw.replace("\\", "/")
    candidate = Path(value)
    if candidate.is_absolute() or re.match(r"[A-Za-z]:/", value):
        try:
            value = candidate.resolve().relative_to(root).as_posix()
        except ValueError as exc:
            raise ModeError(f"path is outside the project: {raw}") from exc
    value = PurePosixPath(value).as_posix().removeprefix("./")
    if value in ("", ".") or ".." in value.split("/"):
        raise ModeError(f"not a project path: {raw}")
    return value


def is_trigger_folder(value: str) -> bool:
    """A folder name that triggers a rule even before it exists (a planned --paths entry without a slash)."""
    folder = value.lower().rstrip("/") + "/"
    known = (*PLAN_DIRS, "docs/designs/", ".github/workflows/", "templates/", "alembic/versions/", *HOOK_PREFIXES)
    return folder in known or folder.split("/")[-2] in ("migrations", "migration")


def path_entries(root: Path, paths: list[str]) -> tuple[list[dict], str]:
    """A plain list: a path that does not exist yet, or that HEAD does not have, counts as added (a plan saved a
    moment ago is new); line counts are unknown."""
    entries = {}
    for raw in paths:
        value = project_relative(root, raw)
        # A folder (existing, or written with a trailing slash) stands for files planned inside it, so the rules
        # see it as "folder/": .github/workflows, migrations and docs/plans then trigger like files in them.
        folder = raw.replace("\\", "/").endswith("/") or (root / value).is_dir() or is_trigger_folder(value)
        key = value + "/" if folder else value
        entries[key] = {"path": key, "status": "M" if os.path.lexists(root / value) else "A", "old_path": None,
                        "lines": 0, "lines_known": False, "folder": folder}
    tracked = head_files(root, [e["path"].rstrip("/") for e in entries.values()]) if entries else None
    if tracked is not None:
        for key, item in entries.items():
            value = key.rstrip("/")
            if item["status"] == "M" and value not in tracked and not any(t.startswith(value + "/") for t in tracked):
                item["status"] = "A"
    return sorted(entries.values(), key=lambda entry: entry["path"]), "path list"


def hook_commands(root: Path) -> list[str]:
    """Commands from Claude Code project settings hooks: the scripts the harness calls."""
    commands = []
    for name in ("settings.json", "settings.local.json"):
        try:
            data = json.loads((root / ".claude" / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        stack = [data.get("hooks")] if isinstance(data, dict) else []
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                if isinstance(item.get("command"), str):
                    commands.append(item["command"])
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)
    return commands


SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}


def command_tokens(command: str) -> list[str]:
    """Shell words of a hook command, plus the words of one `sh -c '...'`-style inner command."""
    def split(text: str) -> list[str]:
        try:
            lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
            lexer.whitespace_split = True
            return list(lexer)
        except ValueError:
            return text.split()

    tokens = split(command)
    inner = []
    for index, token in enumerate(tokens):
        if posixpath.basename(token) not in SHELLS:
            continue
        following = index + 1
        while following < len(tokens) and tokens[following].startswith("-"):
            if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", tokens[following]) and following + 1 < len(tokens):
                inner.extend(split(tokens[following + 1]))
                break
            following += 1
    return tokens + inner


def hook_files(root: Path) -> set[str]:
    """Project-relative paths named in hook commands; hooks run from the project directory."""
    prefixes = ("$CLAUDE_PROJECT_DIR/", "${CLAUDE_PROJECT_DIR}/", root.as_posix().rstrip("/") + "/")
    files = set()
    for command in hook_commands(root):
        for token in command_tokens(command):
            value = token.rsplit("=", 1)[-1].replace("\\", "/")
            value = next((value[len(p):] for p in prefixes if value.startswith(p)), value)
            if not value or value.startswith(("/", "$", "~", "-")) or re.match(r"[A-Za-z]:", value):
                continue
            value = posixpath.normpath(value)
            if value != "." and not value.startswith("../") and value != "..":
                files.add(value)
    return files


def is_doc(path: str) -> bool:
    return path.split("/", 1)[0] == "docs" or PurePosixPath(path).suffix.lower() in DOC_SUFFIXES


def harness_rule(path: str, hooked: set[str]) -> bool:
    name = PurePosixPath(path).name
    if (name in POLICY_NAMES or path.startswith(("templates/", ".github/workflows/", *HOOK_PREFIXES))
            or re.fullmatch(r"\.claude/settings[^/]*\.json", path) or path == ".pre-commit-config.yaml"
            or INSTALLER.fullmatch(name) or (path.startswith("scripts/") and path.count("/") == 1 and name in HARNESS_SCRIPTS)):
        return True
    return path in hooked


def schema_rule(path: str) -> bool:
    parts, name = path.split("/"), PurePosixPath(path).name.lower()
    return (any(part in ("migrations", "migration") for part in parts[:-1]) or "alembic/versions/" in path
            or PurePosixPath(name).stem == "schema" or name.endswith((".schema.json", ".prisma")))


def design_rule(entry: dict) -> bool:
    path, name = entry["path"], PurePosixPath(entry["path"]).name.lower()
    return entry["status"] == "A" and name.endswith(".md") and not path.startswith(NOT_PROJECT_DOCS) and (
        path.startswith("docs/designs/") or fnmatch.fnmatchcase(name, "design*.md"))


def plan_rule(entry: dict) -> bool:
    """A new plan or decision document that the design rule does not already cover (added in 2.0.1). A planned
    folder of design or plan documents (from --paths) counts too: new documents are about to go in it."""
    path, name = entry["path"], PurePosixPath(entry["path"]).name.lower()
    if entry.get("folder"):
        lowered = path.lower()
        return (not path.startswith(NOT_PROJECT_DOCS)
                and any(lowered == d or lowered.startswith(d) for d in (*PLAN_DIRS, "docs/designs/")))
    return (entry["status"] == "A" and name.endswith(".md") and not design_rule(entry)
            and not path.startswith(NOT_PROJECT_DOCS)
            and (path.lower().startswith(PLAN_DIRS) or bool(PLAN_NAME.search(name))))


def plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def listed(paths: list[str], limit: int = 5) -> str:
    shown = ", ".join(paths[:limit])
    return shown + (f" and {len(paths) - limit} more" if len(paths) > limit else "")


def classify(entries: list[dict], hooked: set[str] | None = None) -> dict:
    hooked = hooked or set()
    paths = lambda rule: [e["path"] for e in entries  # noqa: E731
                          if rule(e["path"]) or (e["old_path"] and rule(e["old_path"]))]
    harness = paths(lambda p: harness_rule(p, hooked))
    schema = paths(schema_rule)
    deleted = [e["path"] for e in entries if e["status"] == "D"]
    design = [e["path"] for e in entries if design_rule(e)]
    plans = [e["path"] for e in entries if plan_rule(e)]
    code = [e for e in entries if not is_doc(e["path"])]
    code_lines = sum(e["lines"] for e in code)
    lines_known = all(e["lines_known"] for e in code)
    triggers = []
    if harness:
        triggers.append({"mode": "deep", "rule": "harness", "paths": harness,
                         "reason": "harness or infrastructure that runs on every session: " + listed(harness)})
    if len(deleted) > DEEP_DELETED_FILES:
        triggers.append({"mode": "deep", "rule": "deletions", "paths": deleted,
                         "reason": f"{plural(len(deleted), 'deleted file')} (more than {DEEP_DELETED_FILES}): "
                                   + listed(deleted)})
    if schema:
        triggers.append({"mode": "deep", "rule": "migration-or-schema", "paths": schema,
                         "reason": "migration or schema change: " + listed(schema)})
    if design:
        triggers.append({"mode": "deep", "rule": "new-design-doc", "paths": design,
                         "reason": "new design document: " + listed(design)})
    if plans:
        triggers.append({"mode": "deep", "rule": "new-plan-doc", "paths": plans, "since": "2.0.1",
                         "reason": "new plan or decision document: " + listed(plans)})
    if code_lines >= STANDARD_LINES or len(code) >= STANDARD_FILES:
        triggers.append({"mode": "standard", "rule": "size", "paths": [e["path"] for e in code],
                         "reason": f"code change of {plural(code_lines, 'line')} in {plural(len(code), 'file')} "
                                   f"(threshold {STANDARD_LINES} lines or {STANDARD_FILES} files)"})
    mode = next((m for m in ("deep", "standard") if any(t["mode"] == m for t in triggers)), "light")
    if not entries:
        reasons = ["no changes found; for committed work or a pull request, pass --range BASE..HEAD"]
    elif triggers:
        reasons = [t["reason"] for t in triggers]
    elif not code:
        reasons = [f"documentation only ({plural(len(entries), 'file')})"]
    else:
        reasons = [f"small code change: {plural(code_lines, 'line')} in {plural(len(code), 'file')} "
                   f"(below {STANDARD_LINES} lines and {STANDARD_FILES} files)"]
    if code and not lines_known:
        reasons.append("some line counts are unknown (path list or binary files); only the file count applied to them")
    return {"mode": mode, "reasons": reasons, "triggers": triggers, "design_docs": design + plans, "files": len(entries),
            "code_files": len(code), "code_lines": code_lines, "deleted_files": len(deleted),
            "thresholds": {"standard_lines": STANDARD_LINES, "standard_files": STANDARD_FILES,
                           "deep_deleted_files": DEEP_DELETED_FILES}}


def egm_hosts(root: Path) -> dict[str, bool]:
    """Which hosts have the EGM review entrypoint installed in this project."""
    return {"claude": (root / ".claude/skills/egm-review/SKILL.md").is_file(),
            "codex": (root / ".agents/skills/egm-review/SKILL.md").is_file()}


def _common():
    """oaw_common (installed next to this script): path confinement and locked read-modify-write."""
    folder = str(Path(__file__).resolve().parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    try:
        import oaw_common
    except ImportError as exc:
        raise ModeError("scripts/oaw_common.py is missing; preview `oaw.py migrate`, then --apply, to restore it") from exc
    return oaw_common


def project_file(root: Path, relative: str) -> Path:
    """A project path, refused when '..', an absolute path or a symlink leads outside the project."""
    try:
        return Path(_common().confined_path(root, *PurePosixPath(relative).parts))
    except ValueError as exc:
        raise ModeError(f"{relative}: {exc}") from exc


def read_text(root: Path, relative: str) -> str | None:
    path = project_file(root, relative)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ModeError(f"cannot read {relative}: {exc}") from exc


def update_json(root: Path, relative: str, mutate) -> dict:
    """Read, change and write one JSON file of the project under a process lock, inside the project only."""
    common = _common()
    project_file(root, str(PurePosixPath(relative).parent)).mkdir(parents=True, exist_ok=True)
    project_file(root, relative)
    result = {}

    def apply(text: str) -> str:
        try:
            data = json.loads(text) if text.strip() else {}
        except ValueError as exc:
            raise ModeError(f"{relative} is not readable JSON ({exc}); fix or delete it") from exc
        result["data"] = mutate(data)
        return json.dumps(result["data"], indent=2, ensure_ascii=False) + "\n"

    try:
        common.locked_update(relative, apply, root=root)
    except ValueError as exc:
        raise ModeError(f"{relative}: {exc}") from exc
    except OSError as exc:
        raise ModeError(f"cannot write {relative}: {exc}") from exc
    return result["data"]


def checked_settings(data, source: str) -> dict:
    review = data.get("review", {}) if isinstance(data, dict) else None
    if not isinstance(review, dict):
        raise ModeError(f'{SETTINGS_FILE} must be an object with a "review" object')
    settings = {**DEFAULTS, **{k: v for k, v in review.items() if k in DEFAULTS}, "source": source}
    problems = []
    if settings["egm"] not in EGM_SWITCH:
        problems.append(f"review.egm must be one of {', '.join(EGM_SWITCH)}")
    if isinstance(settings["egm_max_tokens"], bool) or not isinstance(settings["egm_max_tokens"], int) \
            or settings["egm_max_tokens"] <= 0:
        problems.append("review.egm_max_tokens must be a positive whole number")
    if settings["second_opinion"] not in SECOND_OPINIONS:
        problems.append(f"review.second_opinion must be one of {', '.join(SECOND_OPINIONS)}")
    if not isinstance(settings["dry_run"], bool):
        problems.append("review.dry_run must be true or false")
    if problems:
        raise ModeError(f"{SETTINGS_FILE}: " + "; ".join(problems))
    return settings


def load_settings(root: Path) -> dict:
    """The project's review settings: .oaw/settings.json "review", with defaults for anything missing."""
    text = read_text(root, SETTINGS_FILE)
    if text is None:
        return {**DEFAULTS, "source": "default"}
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ModeError(f"{SETTINGS_FILE} is not readable JSON ({exc}); fix or delete it") from exc
    return checked_settings(data, SETTINGS_FILE)


def save_settings(root: Path, **changes) -> dict:
    """Set review settings, keeping every other key of the file; refuses to overwrite a broken file."""
    def mutate(data):
        checked_settings(data, SETTINGS_FILE)
        data.setdefault("review", {}).update(changes)
        checked_settings(data, SETTINGS_FILE)
        return data

    return checked_settings(update_json(root, SETTINGS_FILE, mutate), SETTINGS_FILE)


def file_digest(root: Path, relative: str) -> str | None:
    try:
        return hashlib.sha256(project_file(root, relative).read_bytes()).hexdigest()
    except (OSError, ModeError):
        return None


def _records(data) -> list[dict]:
    records = data.get("reviews") if isinstance(data, dict) else None
    return [r for r in records if isinstance(r, dict)] if isinstance(records, list) else []


def review_records(root: Path) -> list[dict]:
    text = read_text(root, f"{REVIEWS_DIR}/index.json")
    if text is None:
        return []
    try:
        return _records(json.loads(text))
    except ValueError as exc:
        raise ModeError(f"{REVIEWS_DIR}/index.json is not readable JSON ({exc})") from exc


def already_reviewed(root: Path, target: str, how: str) -> dict | None:
    """A finished review of this exact file content by the required kind: a full EGM review counts for any kind,
    a lighter one never counts when EGM is required."""
    digest = file_digest(root, target)
    if digest is None:
        return None
    return next((r for r in reversed(review_records(root))
                 if r.get("target") == target and r.get("sha256") == digest and r.get("status") == "done"
                 and r.get("how") in (how, "egm")), None)


def record_review(root: Path, target: str, how: str, report: str | None, status: str, tokens: int | None) -> dict:
    target = project_relative(root, target)
    project_file(root, target)
    digest = file_digest(root, target)
    if digest is None:
        raise ModeError(f"cannot read the reviewed file: {target}")
    entry = {"target": target, "sha256": digest, "how": how, "status": status, "report": report,
             "tokens": tokens, "recorded": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    update_json(root, f"{REVIEWS_DIR}/index.json",
                lambda data: {"schema_version": 1, "reviews": _records(data) + [entry]})
    return entry


def egm_estimate(total_bytes: int) -> dict:
    """A rough range for one EGM run that reads this many bytes (two calibration points; see the constants)."""
    kilobytes = total_bytes / 1024
    tokens = max(EGM_TOKENS_FLOOR, EGM_TOKENS_BASE + EGM_TOKENS_PER_KB * kilobytes)
    minutes = max(EGM_MINUTES_FLOOR, EGM_MINUTES_BASE + EGM_MINUTES_PER_KB * kilobytes)
    return {"bytes": total_bytes, "tokens_low": int(tokens * ESTIMATE_LOW), "tokens_high": int(tokens * ESTIMATE_HIGH),
            "minutes_low": round(minutes * ESTIMATE_LOW), "minutes_high": round(minutes * ESTIMATE_HIGH),
            "basis": "rough: fitted to two measured EGM runs (Opus 5.5); most of the tokens are cache reads"}


def file_bytes(root: Path, paths: list[str]) -> int:
    total = 0
    for path in paths:
        try:
            total += project_file(root, path).stat().st_size
        except (OSError, ModeError):
            continue
    return total


def inside_project(root: Path, relative: str) -> bool:
    try:
        project_file(root, relative)
    except ModeError:
        return False
    return True


def blob_digest(root: Path, revision: str, relative: str) -> str | None:
    """sha256 of a file's content at a revision (None when the revision does not have it)."""
    try:
        return hashlib.sha256(git(root, "show", f"{revision}:./{relative}")).hexdigest()
    except ModeError:
        return None


def report_dir(root: Path, target: str) -> str:
    identity = hashlib.sha256(f"{target}\0{file_digest(root, target)}".encode("utf-8")).hexdigest()
    return f"{REVIEWS_DIR}/{datetime.now(timezone.utc):%Y-%m-%d}-{slug(target)}-{identity[:10]}/"


def add_plan(result: dict, root: Path, plan: str) -> None:
    """A saved plan named with --plan is a design-review target whatever git says (any project, git or not)."""
    plan = project_relative(root, plan)
    if not project_file(root, plan).is_file():
        raise ModeError(f"--plan is not a file in the project: {plan}")
    if plan not in result["design_docs"]:
        result["design_docs"].append(plan)
    if result["mode"] != "deep":
        result["triggers"].append({"mode": "deep", "rule": "plan-given", "paths": [plan],
                                   "reason": f"a saved plan to review: {plan}"})
        result["reasons"] = [t["reason"] for t in result["triggers"]]
        result["mode"] = "deep"


def slug(path: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", PurePosixPath(path).stem.lower()).strip("-") or "plan"


def second_opinion_review(settings: dict) -> dict:
    """Who reviews code: a fresh session of the same family, or the other family once the user agreed to it."""
    choice = settings["second_opinion"]
    claude = {"same": CLAUDE_REVIEW.removeprefix("review: "), "codex": CODEX_REVIEW.removeprefix("review: "),
              "claude": CLAUDE_REVIEW.removeprefix("review: ")}[choice]
    codex = {"same": CODEX_REVIEW.removeprefix("review: "), "codex": CODEX_REVIEW.removeprefix("review: "),
             "claude": CLAUDE_CROSS_REVIEW}[choice]
    return {"who": "a fresh session of the same model family" if choice == "same" else f"the {choice} family "
            "(the user agreed to send the diff there)", "claude": claude, "codex": codex}


def review_steps(result: dict, root: Path, settings: dict) -> list[dict]:
    """What to do for this mode, and when: steps marked before_code must finish before any code changes."""
    mode, steps = result["mode"], []
    unsized = result.get("source") == "path list" and result.get("code_files", 0) > 0
    if mode == "light":
        if unsized:
            # X3b: a planned path list has no line counts, and agents told "light" before editing skipped the
            # post-change check that would have found a 300+ line change (standard).
            steps.append({"step": "recheck", "before_code": False,
                          "do": "after the change, run python3 scripts/oaw_mode.py suggest on the diff: a path list has "
                                "no line counts, so a large change can still need review"})
        return steps
    if mode == "deep":
        steps.append({"step": "plan", "before_code": True,
                      "do": "plan first (the host's plan mode if it has one); then save the plan as docs/plans/<name>.md"})
        switch = settings["egm"]
        how = {"on": "egm", "off": "none", "auto": AUTO_DESIGN_REVIEW}[switch]
        note = None
        if how == "egm" and not any(egm_hosts(root).values()):
            how, note = "fresh-context", "EGM is not installed in this project: one fresh-context review of the plan instead"
        if how != "none":
            found = result.get("design_docs") or []
            targets = [target for target in found if inside_project(root, target)]
            step = {"step": "design-review", "before_code": True, "how": how, "switch": switch,
                    "targets": targets or ["the plan you save under docs/plans/"], "done": False}
            outside = [target for target in found if target not in targets]
            if outside:
                step["refused"] = {"paths": outside, "why": "a link leads outside the project; not reviewed"}
            if switch == "auto":
                step["basis"] = AUTO_BASIS
            if note:
                step["note"] = note
            if targets:
                # One review per document, each with its own folder named by path and content: EGM reviews one
                # TargetFile at a time and writes fixed file names, so a shared folder would overwrite reports.
                step["reviews"] = []
                for target in targets:
                    review = {"target": target, "report_dir": report_dir(root, target),
                              "done": already_reviewed(root, target, how) is not None}
                    endpoint = result.get("range_end")
                    if endpoint and blob_digest(root, endpoint, target) != file_digest(root, target):
                        # A record is for the working-tree content; the range asks about the endpoint's content.
                        review["done"] = False
                        review["note"] = (f"the working tree differs from {endpoint} for this file: check out "
                                          f"{endpoint} and review that version")
                    step["reviews"].append(review)
                step["done"] = all(review["done"] for review in step["reviews"])
            if how == "egm":
                if targets:
                    estimate = egm_estimate(file_bytes(root, targets))
                    estimate["basis"] += "; the plan only: before running, estimate the plan with its context"
                    step["estimate"] = estimate
                    step["ask_first"] = estimate["tokens_high"] > settings["egm_max_tokens"]
                step["estimate_command"] = ("python3 scripts/oaw_mode.py egm estimate PLAN CONTEXT... --json "
                                            "(ask the user first when it says ask_first)")
                step["do"] = ("run estimate_command with the plan and the context files you will pass, and ask the "
                              "user first when it says ask_first; then follow the installed egm-review skill (its "
                              "bridge file names the runtime) with "
                              "Step: uninterrupted, TargetFile: the plan, GoldfishContext: only the files the plan "
                              "names; write each plan's reports to its report_dir in reviews; resolve the findings "
                              "yourself and hand the user "
                              "only blockers you reject; then run python3 scripts/oaw_mode.py reviewed PLAN --how egm "
                              "--report report_dir. A run cut short is not a review: stop and do not write code.")
            else:
                step["do"] = "have one fresh-context reviewer read the plan and the files it names; resolve the " \
                             "findings; then run python3 scripts/oaw_mode.py reviewed PLAN --how fresh-context"
            steps.append(step)
    review = second_opinion_review(settings)
    steps.append({"step": "code-review", "before_code": False, "rounds": 3 if mode == "deep" else 1,
                  "who": review["who"], "claude": review["claude"], "codex": review["codex"],
                  "do": "after the change, review the diff and tests" + (
                      "; repeat until a round finds nothing new" if mode == "deep" else "")})
    return steps


CLAUDE_CROSS_REVIEW = ("claude -p \"Review the uncommitted changes in this repository, untracked files included "
                       "(git status, git diff HEAD, then read each new file), and their tests for defects; cite "
                       "file:line\" --permission-mode plan --allowedTools Read Grep Glob \"Bash(git status:*)\" "
                       "\"Bash(git diff:*)\" \"Bash(git ls-files:*)\"  (a fresh Claude session; for committed work "
                       "ask for git diff BASE..HEAD instead)")
CLAUDE_REVIEW = ("review: before finishing, start one new subagent with no conversation context; give it only "
                 "the diff (git diff HEAD, or the commit range) and the test command, and have it review both")
CODEX_REVIEW = ("review: codex review --uncommitted  (a fresh-context review; "
                "--base BRANCH or --commit SHA for committed work)")
DEEP_ROUNDS = "after fixes, review again until a round finds nothing new (at most 3 rounds)"
FRESH_DESIGN_REVIEW = ("design review: before any code, one reviewer with no conversation context reads the plan and "
                       "the files it names")
CODEX_PLAN = ("codex --sandbox read-only  (plan in this read-only pass, then implement in a normal session; "
              "Codex plan-mode and effort flags are not mapped yet)")


WINDOWS_SHELL_CHARS = re.compile(r'[$`%!^&|<>()"\';]')


def shell_word(value: str, *, platform: str = os.name) -> str | None:
    """A file name printed inside a command stays one argument and never shell syntax. On Windows the shell
    (cmd or PowerShell) is unknown, and double quotes do not stop $(...), %VAR% or backticks there, so a name
    with those characters gets no command (None): the caller points at the exact path in --json instead."""
    if platform != "nt":
        return shlex.quote(value)
    if WINDOWS_SHELL_CHARS.search(value):
        return None
    return value if re.fullmatch(r"[\w./:@+~-]+", value) else f'"{value}"'


def add_entrypoint(root: PurePath, host: str, *, platform: str = os.name) -> str:
    """The init command that adds a host's entrypoints to this project, with the path quoted for a shell.

    POSIX uses shlex.quote. Windows paths cannot contain double quotes, so they are double-quoted when
    needed; cmd still expands %VAR% and PowerShell $ and backticks inside them, so those get a warning.
    """
    path = root.as_posix()
    if platform != "nt":
        return f"python3 scripts/oaw.py init --target {shlex.quote(path)} --host {host}"
    target = path if re.fullmatch(r"[\w./:@+~-]+", path) else f'"{path}"'
    warning = " (check the quoting: this path contains %, $ or ` that a Windows shell may expand)" \
        if re.search(r"[%$`]", path) else ""
    return f"python3 scripts/oaw.py init --target {target} --host {host}{warning}"


def instructions(mode: str, root: Path, settings: dict | None = None) -> dict:
    """Exact host commands for a mode (flags checked with Claude Code 2.1.287 and codex-cli 0.167.0).

    Deep always plans at the highest effort; its design review follows the EGM switch and falls back to a
    fresh-context review when a host lacks EGM.
    """
    settings = settings or load_settings(root)
    egm = egm_hosts(root)
    switch = settings["egm"]
    how = {"on": "egm", "off": "none", "auto": AUTO_DESIGN_REVIEW}[switch]
    review = second_opinion_review(settings)
    claude_review, codex_review = "review: " + review["claude"], "review: " + review["codex"]
    deep_claude = "claude --permission-mode plan --effort max"
    if mode == "light":
        summary = "light: plain session, no extra review (the default)"
        claude, codex = ["claude"], ["codex"]
    elif mode == "standard":
        summary = "standard: higher effort and one fresh-context review"
        claude = ["claude --effort high", claude_review]
        codex = ["codex  (effort flag not mapped yet)", codex_review]
    elif how == "none":
        summary = "deep: plan first at the highest effort, then code review (the EGM switch is off)"
        claude, codex = [deep_claude, claude_review, DEEP_ROUNDS], [CODEX_PLAN, codex_review, DEEP_ROUNDS]
    elif how == "fresh-context":
        summary = (f"deep: plan first at the highest effort, then one fresh-context design review (EGM switch: "
                   f"{switch}; for full EGM: python3 scripts/oaw_mode.py egm on)")
        claude = [deep_claude, FRESH_DESIGN_REVIEW, claude_review, DEEP_ROUNDS]
        codex = [CODEX_PLAN, FRESH_DESIGN_REVIEW, codex_review, DEEP_ROUNDS]
    elif any(egm.values()):
        summary = f"deep: plan first at the highest effort, then the EGM design review (EGM switch: {switch})"
        if not all(egm.values()):
            missing = "Claude Code" if not egm["claude"] else "Codex"
            summary += f" ({missing} has no EGM entrypoint here: one fresh-context review instead)"
        if egm["claude"]:
            claude = [deep_claude, "design review: the agent runs EGM through the oaw-review skill before any code; "
                                   "to run it yourself, type /egm-review", claude_review, DEEP_ROUNDS]
        else:
            claude = [deep_claude, FRESH_DESIGN_REVIEW, claude_review, DEEP_ROUNDS,
                      "note: EGM's Claude Code entrypoint is not installed here; to add it, run from the OAW checkout: "
                      + add_entrypoint(root, "claude")]
        if egm["codex"]:
            codex = [CODEX_PLAN, "design review: select the egm-review skill in the skill picker", codex_review,
                     DEEP_ROUNDS]
        else:
            codex = [CODEX_PLAN, FRESH_DESIGN_REVIEW, codex_review, DEEP_ROUNDS,
                     "note: EGM's Codex entrypoint is not installed here; to add it, run from the OAW checkout: "
                     + add_entrypoint(root, "codex")]
    else:
        summary = "deep: plan first at the highest effort, then one fresh-context review (EGM is not installed)"
        claude = [deep_claude, FRESH_DESIGN_REVIEW, claude_review, DEEP_ROUNDS]
        codex = [CODEX_PLAN, FRESH_DESIGN_REVIEW, codex_review, DEEP_ROUNDS]
    return {"mode": mode, "summary": summary, "egm": egm, "egm_switch": switch,
            "hosts": {"claude": claude, "codex": codex}}


def render_show(result: dict) -> str:
    lines = [result["summary"]]
    for label, key in (("Claude Code", "claude"), ("Codex", "codex")):
        lines.append(f"{label}:")
        lines.extend("  " + line for line in result["hosts"][key])
    return "\n".join(lines)


def tokens_text(value: int) -> str:
    return f"{value / 1_000_000:.1f}M" if value >= 1_000_000 else f"{value // 1000}k"


def render_steps(steps: list[dict]) -> list[str]:
    lines = []
    for step in steps:
        when = "before code" if step["before_code"] else "after code"
        if step["step"] == "plan":
            lines.append(f"  {when}: plan, then save it under docs/plans/")
        elif step["step"] == "recheck":
            lines.append(f"  {when}: run suggest again on the diff (a path list has no line counts)")
        elif step["step"] == "design-review":
            text = f"  {when}: design review by {REVIEW_NAMES.get(step['how'], step['how'])} (EGM switch: {step['switch']})"
            if step.get("estimate"):
                e = step["estimate"]
                text += (f"; about {tokens_text(e['tokens_low'])}-{tokens_text(e['tokens_high'])} tokens, "
                         f"{e['minutes_low']}-{e['minutes_high']} min")
            if step.get("ask_first"):
                text += "; above this project's cap: ask the user first"
            if step.get("estimate_command"):
                text += "\n    before EGM: " + step["estimate_command"].replace(" --json", "").replace(
                    "(ask the user first when it says ask_first)", "(ask the user first when it says so)")
            if step["done"]:
                text += "  [done for this file content]"
            lines.append(text)
            if step.get("note"):
                lines.append(f"    note: {step['note']}")
            for review in step.get("reviews", []):
                if review["done"]:
                    lines.append(f"    {review['target']}: reviewed")
                else:
                    target, folder = shell_word(review["target"]), shell_word(review["report_dir"])
                    if target is None or folder is None:
                        lines.append(f"    {review['target']}: reports in {review['report_dir']}; when done, run reviewed "
                                     "with the exact path from suggest --json (this name has shell characters)")
                    else:
                        lines.append(f"    {review['target']}: reports in {review['report_dir']}; when done: python3 "
                                     f"scripts/oaw_mode.py reviewed {target} --how {step['how']} --report {folder}")
                if review.get("note"):
                    lines.append(f"      note: {review['note']}")
        else:
            lines.append(f"  {when}: code review by {step['who']}"
                         + (f", up to {step['rounds']} rounds" if step["rounds"] > 1 else ""))
    return lines


def render_suggest(result: dict) -> str:
    lines = [f"mode: {result['mode']}  ({result['source']}: {plural(result['files'], 'file')}, "
             f"{plural(result['code_lines'], 'code line')})"]
    lines.extend("- " + reason for reason in result["reasons"])
    if result.get("steps"):
        lines.append("steps:")
        lines.extend(render_steps(result["steps"]))
    if result.get("dry_run"):
        lines.append("dry run (.oaw/settings.json review.dry_run): run no review and record nothing; still plan first "
                     "when a step says so, and stop before changing code at a design review")
    lines.append(f"how to run it: the oaw-review skill, or python3 scripts/oaw_mode.py show {result['mode']}")
    return "\n".join(lines)


def describe_switch(root: Path, settings: dict) -> dict:
    meaning = {"on": "every deep task gets the full EGM design review before any code",
               "auto": f"deep tasks get the best-evidenced design review: {REVIEW_NAMES[AUTO_DESIGN_REVIEW]} today",
               "off": "EGM never runs; deep tasks get a plan and code review only"}
    installed = any(egm_hosts(root).values())
    result = {"egm": settings["egm"], "meaning": meaning[settings["egm"]], "egm_max_tokens": settings["egm_max_tokens"],
              "second_opinion": settings["second_opinion"], "source": settings["source"], "egm_installed": installed}
    if settings["egm"] == "auto":
        result["basis"] = AUTO_BASIS
    return result


def render_switch(result: dict) -> str:
    lines = [f"EGM switch: {result['egm']}" + ("  (default)" if result["source"] == "default" else ""),
             f"  {result['meaning']}"]
    if result.get("basis"):
        lines.append(f"  why: {result['basis']}")
    lines.append(f"  asks first when one EGM run may exceed {result['egm_max_tokens']:,} tokens")
    wants_egm = {"on": "egm", "off": "none", "auto": AUTO_DESIGN_REVIEW}[result["egm"]] == "egm"
    if wants_egm and not result["egm_installed"]:  # off or a non-EGM auto needs no fallback note (codex review, D37)
        lines.append("  note: EGM is not installed in this project, so deep tasks get a fresh-context review")
    lines.append("  change it: python3 scripts/oaw_mode.py egm on|auto|off   (one EGM run only: type /egm-review)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    suggest = commands.add_parser("suggest", help="pick light, standard or deep from a change",
                                  description="Default: the working tree (staged, unstaged and untracked files) "
                                              "against HEAD; pass --range for committed work. " + SUGGEST_EXAMPLES)
    source = suggest.add_mutually_exclusive_group()
    source.add_argument("--range", dest="revision_range", metavar="A..B", help="a git revision range instead")
    source.add_argument("--paths", nargs="+", metavar="PATH",
                        help="a plain path list (planned or changed); a missing path counts as new")
    suggest.add_argument("--plan", metavar="FILE",
                         help="a saved plan to review before code: always a design-review target (works without git)")
    show = commands.add_parser("show", help="print how to run a mode")
    show.add_argument("mode", choices=MODES)
    egm = commands.add_parser("egm", help="show or set the EGM switch (on, auto, off), or estimate one EGM run",
                              description="on: every deep task gets the full EGM design review. auto (default): the "
                                          "best-evidenced design review, one fresh-context review until the X2 "
                                          "study decides. off: never EGM. "
                                          "estimate FILE...: a rough cost for one EGM run reading those files.")
    egm.add_argument("action", nargs="?", choices=(*EGM_SWITCH, "estimate"))
    egm.add_argument("files", nargs="*", metavar="FILE", help="with estimate: the plan and its context files")
    egm.add_argument("--max-tokens", type=int, metavar="N", help="ask first when one EGM run may exceed N tokens")
    opinion = commands.add_parser("second-opinion", help="who reviews code: same family (default), codex or claude",
                                  description="codex or claude sends diffs to that family under your own login; "
                                              "setting it is your consent.")
    opinion.add_argument("who", nargs="?", choices=SECOND_OPINIONS)
    reviewed = commands.add_parser("reviewed", help="record a finished design review of a file's current content")
    reviewed.add_argument("target", help="the reviewed plan or design file, relative to the project")
    reviewed.add_argument("--how", required=True, choices=("egm", "fresh-context", "checklist", "cross-family"))
    reviewed.add_argument("--report", help="where the review report was written")
    reviewed.add_argument("--status", default="done", choices=("done", "cut"),
                          help="cut: stopped early (a usage limit, for example); it does not count as reviewed")
    reviewed.add_argument("--tokens", type=int, help="tokens the review used, if known")
    for sub in (suggest, show, egm, opinion, reviewed):
        sub.add_argument("--root", help="project directory (default: the folder that holds this script's scripts/ folder)")
        sub.add_argument("--json", action="store_true", help="print a machine-readable result")
    args = parser.parse_args(argv)
    try:
        root = project_root(args.root)
        if args.command == "show":
            result = instructions(args.mode, root)
            text = render_show(result)
        elif args.command == "egm":
            if args.action == "estimate":
                if not args.files:
                    raise ModeError("estimate needs the plan and its context files")
                missing = [path for path in args.files if not project_file(root, path).is_file()]
                if missing:
                    raise ModeError("not a file in the project: " + ", ".join(missing))
                cap = load_settings(root)["egm_max_tokens"]
                result = egm_estimate(file_bytes(root, args.files))
                result.update({"egm_max_tokens": cap, "ask_first": result["tokens_high"] > cap})
                text = (f"one EGM run reading {result['bytes']:,} bytes: about {tokens_text(result['tokens_low'])}-"
                        f"{tokens_text(result['tokens_high'])} tokens, {result['minutes_low']}-{result['minutes_high']} "
                        f"min ({result['basis']})"
                        + (f"\nabove this project's cap of {cap:,} tokens: ask the user first" if result["ask_first"] else ""))
            else:
                if args.files:
                    raise ModeError("files are only for estimate")
                if args.max_tokens is not None and args.max_tokens <= 0:
                    raise ModeError("--max-tokens must be positive")
                changes = {key: value for key, value in (("egm", args.action), ("egm_max_tokens", args.max_tokens))
                           if value is not None}
                settings = save_settings(root, **changes) if changes else load_settings(root)
                result = describe_switch(root, settings)
                text = render_switch(result)
        elif args.command == "second-opinion":
            settings = save_settings(root, second_opinion=args.who) if args.who else load_settings(root)
            result = {"second_opinion": settings["second_opinion"], **second_opinion_review(settings)}
            text = f"code review: {result['who']}\n  Claude Code: {result['claude']}\n  Codex: {result['codex']}"
        elif args.command == "reviewed":
            result = record_review(root, args.target, args.how, args.report, args.status, args.tokens)
            text = (f"recorded: {result['target']} reviewed by {result['how']} ({result['status']})"
                    + ("" if result["status"] == "done" else "; it does not count until a full review is recorded"))
        else:
            if args.paths:
                entries, label = path_entries(root, args.paths)
            elif args.plan and args.revision_range is None and not in_git(root):
                entries, label = [], "a saved plan only (not a git repository)"
            else:
                entries, label = diff_entries(root, args.revision_range)
            settings = load_settings(root)
            result = {"schema_version": 1, "source": label, **classify(entries, hook_files(root))}
            if args.revision_range:
                result["range_end"] = args.revision_range.split("..")[-1].lstrip(".") or "HEAD"
            if args.plan:
                add_plan(result, root, args.plan)
            result["settings"] = {k: settings[k] for k in DEFAULTS}
            result["steps"] = review_steps(result, root, settings)
            result["dry_run"] = settings["dry_run"]
            text = render_suggest(result)
    except ModeError as exc:
        print(f"oaw_mode: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
