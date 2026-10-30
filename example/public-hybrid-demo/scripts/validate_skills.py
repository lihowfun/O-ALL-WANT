#!/usr/bin/env python3
"""Validate OAW's portable native skill packages using the standard library.

This is a deliberately small frontmatter validator, not a full YAML parser or a
host compatibility certification. Supported fields are name, description,
license, compatibility, allowed-tools (strings), disable-model-invocation (a
boolean), and metadata (a string map).
Strings may be plain, quoted, or indented literal/folded blocks. Host-specific
frontmatter and other YAML constructs need the host's own validator.
"""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


SCALAR_FIELDS = {"name", "description", "license", "compatibility", "allowed-tools"}
BOOLEAN_FIELDS = {"disable-model-invocation"}
NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
FIELD_RE = re.compile(r"([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]+(.*))?\Z")
LINK_RE = re.compile(r"!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)")


def _scalar(value):
    """Read a string in the supported YAML subset; fail instead of guessing."""
    value = value.strip()
    if not value:
        raise ValueError("empty scalar; quote an intentionally empty string")
    if value.startswith('"'):
        try:
            result = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid double-quoted scalar") from exc
        if not isinstance(result, str):
            raise ValueError("expected a string")
        return result
    if value.startswith("'"):
        if not re.fullmatch(r"'(?:[^']|'')*'", value):
            raise ValueError("invalid single-quoted scalar")
        return value[1:-1].replace("''", "'")
    value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
    if not value or value.startswith(("[", "{", "&", "*", "!", "#")):
        raise ValueError("expected a string; collections, tags and aliases are unsupported")
    if ": " in value or value.lower() in {"true", "false", "null", "~"}:
        raise ValueError("quote this scalar to make its string type unambiguous")
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value):
        raise ValueError("expected a string, not a number")
    return value


def _frontmatter(content):
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing opening YAML frontmatter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing YAML frontmatter delimiter") from exc
    fields = {}
    index = 1
    while index < end:
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        match = FIELD_RE.fullmatch(line)
        if not match:
            raise ValueError("invalid or unsupported frontmatter at line %d" % (index + 1))
        key, value = match.group(1), (match.group(2) or "")
        if key in fields:
            raise ValueError("duplicate frontmatter field: %s" % key)
        if key not in SCALAR_FIELDS | BOOLEAN_FIELDS | {"metadata"}:
            raise ValueError("unsupported portable frontmatter field: %s" % key)
        index += 1
        nested = []
        while index < end and (not lines[index].strip() or lines[index].startswith(" ")):
            nested.append(lines[index])
            index += 1
        if key in BOOLEAN_FIELDS:
            if value.strip() not in {"true", "false"} or any(item.strip() for item in nested):
                raise ValueError("expected a boolean for %s" % key)
            fields[key] = value.strip() == "true"
        elif key == "metadata":
            if value.strip() == "{}" and not any(item.strip() for item in nested):
                fields[key] = {}
                continue
            if value.strip():
                raise ValueError("metadata must be an indented string map")
            mapping = {}
            for item in nested:
                if not item.strip() or item.lstrip().startswith("#"):
                    continue
                field = FIELD_RE.fullmatch(item[2:]) if item.startswith("  ") else None
                if not field or field.group(1) in mapping:
                    raise ValueError("invalid or duplicate metadata entry")
                mapping[field.group(1)] = _scalar(field.group(2) or "")
            fields[key] = mapping
        elif value.strip() in {">", ">-", ">+", "|", "|-", "|+"}:
            nonempty = [item for item in nested if item.strip()]
            if not nonempty:
                raise ValueError("empty block scalar for %s" % key)
            indent = min(len(item) - len(item.lstrip(" ")) for item in nonempty)
            text = [item[indent:] if item.strip() else "" for item in nested]
            separator = " " if value.strip().startswith(">") else "\n"
            fields[key] = separator.join(text).strip()
        else:
            if any(item.strip() for item in nested):
                raise ValueError("unsupported nested value for %s" % key)
            fields[key] = _scalar(value)
    return fields, "\n".join(lines[end + 1:])


def find_skill_files(base_dir, *, managed_only=False):
    """Find canonical framework packages, or installed native skill packages.

    Return expected SKILL.md paths for directories even when missing, so empty
    or malformed packages cannot silently disappear from lint. Legacy flat
    Markdown files are included so lint reports their unsupported location.
    With managed_only, an installed project's manifest defines the scope;
    unrelated host/plugin skills are not subject to OAW's portable YAML subset.
    """
    base = Path(base_dir)
    canonical = base / "templates" / ".agents" / "skills"
    if managed_only and not canonical.is_dir():
        manifest = base / ".oaw" / "install.json"
        if not manifest.is_file():
            return []
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("Invalid OAW installation manifest")
        managed, custom = data.get("managed_files"), data.get("custom_files", [])
        if not isinstance(managed, dict) or not isinstance(custom, list):
            raise ValueError("Invalid managed/custom file inventory")
        if any(not isinstance(path, str) for path in [*managed, *custom]):
            raise ValueError("Invalid path in OAW installation manifest")
        found = []
        for relative in sorted(set(managed) | set(custom)):
            if not isinstance(relative, str) or "\\" in relative or ":" in relative or any(
                    part in ("", ".", "..") for part in relative.split("/")):
                raise ValueError("Unsafe path in OAW installation manifest")
            if re.fullmatch(r"\.(?:agents|claude)/skills/[^/]+/SKILL\.md", relative):
                found.append(str((base / relative).absolute()))
        return found
    roots = [canonical] if canonical.is_dir() else [
        base / ".agents" / "skills", base / ".claude" / "skills"
    ]
    found = []
    seen = set()
    for root in roots:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if child.name.startswith(".") or child.name.lower() == "readme.md":
                continue
            target = child / "SKILL.md" if child.is_dir() else child
            if not child.is_dir() and child.suffix.lower() != ".md":
                continue
            identity = str(target.resolve())
            if identity not in seen:
                seen.add(identity)
                found.append(str(target.absolute()))
    return found


def _without_fences(content):
    result = []
    fence = None
    for line in content.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            result.append(line)
    return "\n".join(result)


def _reference_issues(skill_file, body):
    package = skill_file.parent.resolve()
    pending = [(skill_file, body)]
    seen = set()
    issues = []
    while pending:
        source, content = pending.pop()
        if source.resolve() in seen:
            continue
        seen.add(source.resolve())
        for match in LINK_RE.finditer(_without_fences(content)):
            destination = match.group(1).strip("<>")
            if re.match(r"^[A-Za-z]:[\\/]", destination) or destination.startswith("\\\\"):
                issues.append("local reference must be package-relative: %s" % destination)
                continue
            try:
                parsed = urlsplit(destination)
            except ValueError:
                issues.append("malformed reference URL: %s" % destination)
                continue
            if parsed.scheme and parsed.scheme.lower() != "file":
                continue
            if parsed.scheme.lower() == "file" or parsed.path.startswith("/") and not destination.startswith("//"):
                issues.append("local reference must be package-relative: %s" % destination)
                continue
            if destination.startswith("//") or not parsed.path:
                continue
            target = (source.parent / unquote(parsed.path)).resolve()
            try:
                target.relative_to(package)
            except ValueError:
                issues.append("local reference escapes skill package: %s" % destination)
                continue
            if not target.is_file():
                issues.append("local reference is missing or not a file: %s" % destination)
            elif target.suffix.lower() == ".md" and target not in seen:
                try:
                    pending.append((target, target.read_text(encoding="utf-8-sig")))
                except (OSError, UnicodeError) as exc:
                    issues.append("cannot read local reference %s: %s" % (destination, exc))
    return issues


def lint_skill_file(path):
    """Return diagnostics for one native package; an empty list means valid."""
    skill_file = Path(path)
    if skill_file.name != "SKILL.md":
        return ["native skill must be a folder containing SKILL.md: %s" % path]
    if not skill_file.is_file():
        return ["SKILL.md is missing or not a file: %s" % path]
    try:
        skill_file.resolve().relative_to(skill_file.parent.resolve())
    except ValueError:
        return ["SKILL.md resolves outside its package: %s" % path]
    try:
        content = skill_file.read_text(encoding="utf-8-sig")
        fields, body = _frontmatter(content)
    except (OSError, UnicodeError, ValueError) as exc:
        return ["%s: %s" % (path, exc)]
    issues = []
    name = fields.get("name", "")
    if not name or len(name) > 64 or not NAME_RE.fullmatch(name):
        issues.append("name must be 1-64 lowercase letters/digits with single separating hyphens")
    if name != skill_file.parent.name:
        issues.append("name must match the skill folder: %s" % skill_file.parent.name)
    description = fields.get("description", "")
    if not description.strip() or len(description) > 1024:
        issues.append("description must be a nonempty string of at most 1024 characters")
    if "<" in description or ">" in description:
        issues.append("description must not contain angle brackets")
    if not body.strip():
        issues.append("skill body is empty")
    if re.search(r"(?m)^\s*\[TODO:[^\n]*\]\s*$", _without_fences(body)):
        issues.append("skill body contains an unfinished TODO scaffold")
    issues.extend(_reference_issues(skill_file, body))
    return issues


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_dir", nargs="?", default=str(Path(__file__).resolve().parent.parent),
                        help="project or framework root (default: this script's project)")
    parser.add_argument("--all-packages", action="store_true",
                        help="apply OAW's portable subset to all local packages, including third-party skills; not host certification")
    args = parser.parse_args(argv)
    installed = (Path(args.base_dir) / ".oaw/install.json").is_file()
    try:
        paths = find_skill_files(args.base_dir, managed_only=installed and not args.all_packages)
    except (OSError, ValueError, TypeError) as exc:
        print("ERROR: %s" % exc)
        return 1
    failed = False
    for path in paths:
        for issue in lint_skill_file(path):
            print("ERROR: %s" % issue)
            failed = True
    if not failed:
        print("Validated %d portable native skill package(s)." % len(paths))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
