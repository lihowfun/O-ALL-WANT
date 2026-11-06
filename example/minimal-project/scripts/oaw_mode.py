#!/usr/bin/env python3
"""Pick a working mode (light, standard or deep) from a change, and print how to run it.

Light is the default. `suggest` applies fixed rules to a git diff or a path list:

  deep      harness or infrastructure that runs on every session, an
            irreversible-looking change, or a new design document
  standard  a code change of 300+ lines or 10+ files with no deep trigger
  light     everything else, including docs-only and small changes

`show MODE` prints the host commands for that mode. Deep names the EGM review
only for a host whose `egm-review` entrypoint is installed in this project.

Part of OAW. https://github.com/lihowfun/O-ALL-WANT
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

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
INSTALLER = re.compile(r"(?i)^(?:install|setup|bootstrap)(?:[._-][^/]*)?\.(?:sh|ps1|bat|cmd|py)$")
UNTRACKED_LINE_LIMIT = 1_000_000  # bytes; larger untracked files count as files without line counts
SUGGEST_EXAMPLES = "Examples: --range main..HEAD, --paths docs/a.md scripts/b.py"


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
    if value:
        root = Path(value).resolve()
        if not root.is_dir():
            raise ModeError(f"root is not a directory: {value}")
        return root
    try:
        process = subprocess.run(["git", "rev-parse", "--show-toplevel"], stdin=subprocess.DEVNULL,
                                 capture_output=True, check=False)
    except OSError:
        return Path.cwd().resolve()
    top = process.stdout.decode("utf-8", "replace").strip()
    return Path(top).resolve() if process.returncode == 0 and top else Path.cwd().resolve()


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
    options = ["--no-ext-diff", "--no-textconv", "--find-renames", "-z"]
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


def path_entries(root: Path, paths: list[str]) -> tuple[list[dict], str]:
    """A plain list: a path that does not exist yet counts as added; line counts are unknown."""
    entries = {}
    for raw in paths:
        value = raw.replace("\\", "/")
        candidate = Path(value)
        if candidate.is_absolute():
            try:
                value = candidate.resolve().relative_to(root).as_posix()
            except ValueError as exc:
                raise ModeError(f"path is outside the project: {raw}") from exc
        value = PurePosixPath(value).as_posix().removeprefix("./")
        if value in ("", ".") or ".." in value.split("/"):
            raise ModeError(f"not a project path: {raw}")
        exists = os.path.lexists(root / value)
        entries[value] = {"path": value, "status": "M" if exists else "A", "old_path": None,
                          "lines": 0, "lines_known": False}
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


def is_doc(path: str) -> bool:
    return path.split("/", 1)[0] == "docs" or PurePosixPath(path).suffix.lower() in DOC_SUFFIXES


def harness_rule(path: str, commands: list[str]) -> bool:
    name = PurePosixPath(path).name
    if (name in POLICY_NAMES or path.startswith(("templates/", ".github/workflows/", *HOOK_PREFIXES))
            or re.fullmatch(r"\.claude/settings[^/]*\.json", path) or path == ".pre-commit-config.yaml"
            or INSTALLER.fullmatch(name) or (path.startswith("scripts/") and path.count("/") == 1 and name in HARNESS_SCRIPTS)):
        return True
    pattern = re.compile(r"(?<![\w.-])" + re.escape(path) + r"(?![\w.-])")
    return any(pattern.search(command) for command in commands)


def schema_rule(path: str) -> bool:
    parts, name = path.split("/"), PurePosixPath(path).name.lower()
    return (any(part in ("migrations", "migration") for part in parts[:-1]) or "alembic/versions/" in path
            or PurePosixPath(name).stem == "schema" or name.endswith((".schema.json", ".prisma")))


def design_rule(entry: dict) -> bool:
    path, name = entry["path"], PurePosixPath(entry["path"]).name.lower()
    return entry["status"] == "A" and name.endswith(".md") and (
        path.startswith("docs/designs/") or fnmatch.fnmatchcase(name, "design*.md"))


def plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def listed(paths: list[str], limit: int = 5) -> str:
    shown = ", ".join(paths[:limit])
    return shown + (f" and {len(paths) - limit} more" if len(paths) > limit else "")


def classify(entries: list[dict], commands: list[str] | None = None) -> dict:
    commands = commands or []
    paths = lambda rule: [e["path"] for e in entries  # noqa: E731
                          if rule(e["path"]) or (e["old_path"] and rule(e["old_path"]))]
    harness = paths(lambda p: harness_rule(p, commands))
    schema = paths(schema_rule)
    deleted = [e["path"] for e in entries if e["status"] == "D"]
    design = [e["path"] for e in entries if design_rule(e)]
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
    if code_lines >= STANDARD_LINES or len(code) >= STANDARD_FILES:
        triggers.append({"mode": "standard", "rule": "size", "paths": [e["path"] for e in code],
                         "reason": f"code change of {plural(code_lines, 'line')} in {plural(len(code), 'file')} "
                                   f"(threshold {STANDARD_LINES} lines or {STANDARD_FILES} files)"})
    mode = next((m for m in ("deep", "standard") if any(t["mode"] == m for t in triggers)), "light")
    if not entries:
        reasons = ["no changes found"]
    elif triggers:
        reasons = [t["reason"] for t in triggers]
    elif not code:
        reasons = [f"documentation only ({plural(len(entries), 'file')})"]
    else:
        reasons = [f"small code change: {plural(code_lines, 'line')} in {plural(len(code), 'file')} "
                   f"(below {STANDARD_LINES} lines and {STANDARD_FILES} files)"]
    if code and not lines_known:
        reasons.append("some line counts are unknown (path list or binary files); only the file count applied to them")
    return {"mode": mode, "reasons": reasons, "triggers": triggers, "files": len(entries),
            "code_files": len(code), "code_lines": code_lines, "deleted_files": len(deleted),
            "thresholds": {"standard_lines": STANDARD_LINES, "standard_files": STANDARD_FILES,
                           "deep_deleted_files": DEEP_DELETED_FILES}}


def egm_hosts(root: Path) -> dict[str, bool]:
    """Which hosts have the EGM review entrypoint installed in this project."""
    return {"claude": (root / ".claude/skills/egm-review/SKILL.md").is_file(),
            "codex": (root / ".agents/skills/egm-review/SKILL.md").is_file()}


CLAUDE_REVIEW = ("review: before finishing, start one new subagent with no conversation context; give it only "
                 "the diff (git diff HEAD, or the commit range) and the test command, and have it review both")
CODEX_REVIEW = ("review: codex review --uncommitted  (a fresh-context review; "
                "--base BRANCH or --commit SHA for committed work)")
CODEX_PLAN = ("codex --sandbox read-only  (plan in this read-only pass, then implement in a normal session; "
              "Codex plan-mode and effort flags are not mapped yet)")


def instructions(mode: str, root: Path) -> dict:
    """Exact host commands for a mode (flags checked with Claude Code 2.1.287 and codex-cli 0.167.0)."""
    egm = egm_hosts(root)
    if mode == "light":
        summary = "light: plain session, no extra review (the default)"
        claude, codex = ["claude"], ["codex"]
    elif mode == "standard":
        summary = "standard: higher effort and one fresh-context review"
        claude = ["claude --effort high", CLAUDE_REVIEW]
        codex = ["codex  (effort flag not mapped yet)", CODEX_REVIEW]
    elif any(egm.values()):
        summary = "deep: plan first at the highest effort, then the EGM review"
        if not all(egm.values()):
            missing = "Claude Code" if not egm["claude"] else "Codex"
            summary += f" ({missing} has no EGM entrypoint here: standard plus plan mode)"
        if egm["claude"]:
            claude = ["claude --permission-mode plan --effort max",
                      "review: type /egm-review  (explicit invocation only; the agent cannot start it)"]
        else:
            claude = ["claude --permission-mode plan --effort high", CLAUDE_REVIEW,
                      "note: EGM's Claude Code entrypoint is not installed here; "
                      "oaw.py init --host claude, run from the OAW checkout, adds it"]
        if egm["codex"]:
            codex = [CODEX_PLAN, "review: select the egm-review skill in the skill picker"]
        else:
            codex = [CODEX_PLAN, CODEX_REVIEW,
                     "note: EGM's Codex entrypoint is not installed here; "
                     "oaw.py init --host codex, run from the OAW checkout, adds it"]
    else:
        summary = "deep: plan first, then one fresh-context review (EGM is not installed: standard plus plan mode)"
        claude = ["claude --permission-mode plan --effort high", CLAUDE_REVIEW]
        codex = [CODEX_PLAN, CODEX_REVIEW]
    return {"mode": mode, "summary": summary, "egm": egm, "hosts": {"claude": claude, "codex": codex}}


def render_show(result: dict) -> str:
    lines = [result["summary"]]
    for label, key in (("Claude Code", "claude"), ("Codex", "codex")):
        lines.append(f"{label}:")
        lines.extend("  " + line for line in result["hosts"][key])
    return "\n".join(lines)


def render_suggest(result: dict) -> str:
    lines = [f"mode: {result['mode']}  ({result['source']}: {plural(result['files'], 'file')}, "
             f"{plural(result['code_lines'], 'code line')})"]
    lines.extend("- " + reason for reason in result["reasons"])
    lines.append(f"how to run it: python3 scripts/oaw_mode.py show {result['mode']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    suggest = commands.add_parser("suggest", help="pick light, standard or deep from a change",
                                  description="Default: the working tree (staged, unstaged and untracked files) "
                                              "against HEAD. " + SUGGEST_EXAMPLES)
    source = suggest.add_mutually_exclusive_group()
    source.add_argument("--range", dest="revision_range", metavar="A..B", help="a git revision range instead")
    source.add_argument("--paths", nargs="+", metavar="PATH",
                        help="a plain path list (planned or changed); a missing path counts as new")
    show = commands.add_parser("show", help="print how to run a mode")
    show.add_argument("mode", choices=MODES)
    for sub in (suggest, show):
        sub.add_argument("--root", help="project directory (default: the git top level, else the current directory)")
        sub.add_argument("--json", action="store_true", help="print a machine-readable result")
    args = parser.parse_args(argv)
    try:
        root = project_root(args.root)
        if args.command == "show":
            result = instructions(args.mode, root)
            text = render_show(result)
        else:
            if args.paths:
                entries, label = path_entries(root, args.paths)
            else:
                entries, label = diff_entries(root, args.revision_range)
            result = {"schema_version": 1, "source": label, **classify(entries, hook_commands(root))}
            text = render_suggest(result)
    except ModeError as exc:
        print(f"oaw_mode: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
