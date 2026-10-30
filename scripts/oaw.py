#!/usr/bin/env python3
"""Safe OAW bootstrap. Run from the framework checkout; this CLI stays there.

Init never overwrites different existing content. Migrate previews by default;
--apply backs up recognized replacements and stages custom-content proposals.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import uuid

FRAMEWORK_ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK_VERSION = "2.0.0"
MANIFEST_PATH = ".oaw/install.json"
PROFILES = ("minimal", "knowledge")
HOSTS = ("codex", "claude")
EGM_COMMIT = "f0ba151b252c9abf1318d9fe857a43265d06de89"
EGM_LOCK_SHA256 = "c6ff4b7b56ce8187e842baa190c0b3fda2a37d112450931839e43bd7faf3d25e"
EGM_RUNTIME = ".oaw/integrations/egm/"
EGM_SKILLS = ("egm-bootstrap", "egm-brainstorm", "egm-draft", "egm-drift-report", "egm-resolve", "egm-review", "egm-review-loop")
BUNDLED_SKILLS = (*EGM_SKILLS, "oaw-evidence", "oaw-wiki", "oaw-improve")
ALWAYS_PRESERVE = {"AI_CONTEXT.md", "VERSION.json", "ROADMAP.md", ".agents/memory.md"}
LEGACY_ADAPTERS = {"GEMINI.md", ".cursorrules", ".windsurfrules", ".github/copilot-instructions.md"}


class InstallError(Exception):
    """A preflight/installation failure safe to show without a traceback."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def imports_agents(data: bytes) -> bool:
    """Whether a Claude adapter imports the shared AGENTS.md policy."""
    return re.search(rb"(?m)(?:^|\s)@(?:\./)?AGENTS\.md(?![\w/-])", data) is not None


def selected_hosts(hosts: list[str] | None = None) -> list[str]:
    hosts = ["codex"] if hosts is None else hosts
    if (not isinstance(hosts, list) or not hosts or any(host not in HOSTS for host in hosts)
            or len(set(hosts)) != len(hosts)):
        raise InstallError("Hosts must be a nonempty list containing codex and/or claude.")
    return [host for host in HOSTS if host in hosts]


def relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise InstallError(f"Unsafe managed path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("", ".", "..") for p in value.split("/")):
        raise InstallError(f"Unsafe managed path: {value!r}")
    return path


def joined(root: Path, relative: str) -> Path:
    return root.joinpath(*relative_path(relative).parts)


def is_path_alias(path: Path) -> bool:
    """Recognize a selected symlink or Windows junction without following it."""
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def framework_root() -> Path:
    # __file__ is normally canonical already; keep explicit/test source roots so
    # too. OS aliases above this selected root are not project descendants.
    return FRAMEWORK_ROOT.resolve()


def check_path(path: Path, *, kind: str | None = None) -> None:
    """Reject symlink/junction traversal and type conflicts before any mutation."""
    for part in [*reversed(path.parents), path]:
        if not os.path.lexists(part):
            continue
        if is_path_alias(part):
            raise InstallError(f"Symlink/junction traversal refused: {part}")
        if part != path and not part.is_dir():
            raise InstallError(f"Parent path is not a directory: {part}")
    if os.path.lexists(path):
        if kind == "file" and not path.is_file():
            raise InstallError(f"Expected a regular file, found a directory/special path: {path}")
        if kind == "dir" and not path.is_dir():
            raise InstallError(f"Expected a directory: {path}")


def target_path(value: str | Path) -> Path:
    selected = Path(os.path.abspath(value))
    # Resolve ancestry such as macOS /var -> /private/var, but never hide an
    # explicitly selected symlink/junction project root with resolve(). Managed
    # descendant paths remain lexical joins and check_path still rejects them.
    if os.path.lexists(selected) and is_path_alias(selected):
        raise InstallError(f"Symlink/junction traversal refused: {selected}")
    target = selected.parent.resolve() / selected.name
    check_path(target, kind="dir")
    if target == framework_root():
        raise InstallError("Refusing to install into the OAW framework repository itself.")
    check_path(target / ".oaw", kind="dir")
    return target


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstallError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InstallError(f"Expected a JSON object: {path}")
    return data


def read_manifest(target: Path) -> dict | None:
    path = joined(target, MANIFEST_PATH)
    check_path(path, kind="file")
    if not path.exists():
        return None
    data = read_json(path)
    if data.get("schema_version") != 1 or not isinstance(data.get("framework_version"), str):
        raise InstallError("Unsupported/invalid install manifest schema or framework version.")
    if data.get("profile") not in PROFILES or not isinstance(data.get("with_improve"), bool):
        raise InstallError("Invalid profile/with_improve in install manifest.")
    if not isinstance(data.get("hosts", ["codex"]), list):
        raise InstallError("Invalid hosts in install manifest.")
    selected_hosts(data.get("hosts", ["codex"]))
    if "skills" in data:
        selected_skills(data["skills"])
        if not isinstance(data.get("skills_explicit", True), bool):
            raise InstallError("Invalid skills_explicit in install manifest.")
    integrations = data.get("integrations", {})
    if not isinstance(integrations, dict):
        raise InstallError("Invalid integrations in install manifest.")
    if "egm" in integrations and integrations["egm"] != {"commit": EGM_COMMIT, "version": "0.1.0", "source_lock_sha256": EGM_LOCK_SHA256}:
        raise InstallError("Unknown or modified EGM integration identity.")
    managed = data.get("managed_files")
    if not isinstance(managed, dict):
        raise InstallError("Invalid managed_files in install manifest.")
    for relative, checksum in managed.items():
        relative_path(relative)
        if (relative.startswith(".oaw/") and not relative.startswith(EGM_RUNTIME)) or relative in ALWAYS_PRESERVE:
            raise InstallError(f"Reserved/unmanaged path in install manifest: {relative}")
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise InstallError(f"Invalid SHA-256 for managed path: {relative}")
        check_path(joined(target, relative), kind="file")
    custom = data.get("custom_files", [])
    if not isinstance(custom, list) or any(not isinstance(path, str) for path in custom) or len(set(custom)) != len(custom):
        raise InstallError("Invalid custom_files in install manifest.")
    for relative in custom:
        relative_path(relative)
        if (relative.startswith(".oaw/") and not relative.startswith(EGM_RUNTIME)) or relative in ALWAYS_PRESERVE or relative in managed:
            raise InstallError(f"Reserved or simultaneously managed/custom path: {relative}")
        check_path(joined(target, relative), kind="file")
    return data


def default_skills(profile: str, with_improve: bool) -> list[str]:
    return [*EGM_SKILLS, "oaw-evidence", *(["oaw-wiki"] if profile == "knowledge" else []), *(["oaw-improve"] if with_improve else [])]


def selected_skills(skills: list[str]) -> list[str]:
    if not isinstance(skills, list) or any(not isinstance(s, str) or s not in BUNDLED_SKILLS for s in skills) or len(set(skills)) != len(skills):
        raise InstallError("Skills must be a unique list of bundled skill names; inspect `oaw.py skills`.")
    return sorted(skills)


def egm_native_agents() -> dict[str, str]:
    """Native Claude adapter paths declared by the pinned upstream manifest."""
    package = egm_payload()
    manifest = json.loads(package[EGM_RUNTIME + ".claude-plugin/plugin.json"].decode("utf-8"))
    result = {}
    for reference in manifest.get("agents", []):
        relative = PurePosixPath(reference).as_posix().removeprefix("./")
        text = package[EGM_RUNTIME + relative].decode("utf-8")
        match = re.search(r"(?m)^name:\s*(egm-[a-z0-9-]+)\s*$", text)
        if not match:
            raise InstallError("Invalid native EGM agent identity.")
        result[f".claude/agents/{match.group(1)}.md"] = f"templates/.claude/agents/{match.group(1)}.md"
    return result


def egm_payload(root: Path | None = None) -> dict[str, bytes]:
    """Validate a complete immutable upstream runtime against an independent pin."""
    root = framework_root() / "vendor/egm" if root is None else root
    check_path(root, kind="dir")
    lock_path = root / "OAW_SOURCE.json"
    check_path(lock_path, kind="file")
    if not lock_path.is_file() or digest(lock_path.read_bytes()) != EGM_LOCK_SHA256:
        raise InstallError("Pinned EGM provenance is missing or changed.")
    lock = read_json(lock_path)
    if lock.get("commit") != EGM_COMMIT or lock.get("version") != "0.1.0" or lock.get("license") != "Apache-2.0" or set(lock.get("skills", [])) != set(EGM_SKILLS):
        raise InstallError("Pinned EGM identity does not match V2.")
    expected = lock["files"]
    observed = set()
    for path in root.rglob("*"):
        check_path(path)
        if path.is_file():
            check_path(path, kind="file")
            observed.add(path.relative_to(root).as_posix())
    if observed != set(expected) | {"OAW_SOURCE.json"}:
        raise InstallError("Pinned EGM runtime has missing or unlisted files.")
    result = {EGM_RUNTIME + "OAW_SOURCE.json": lock_path.read_bytes()}
    for relative, checksum in expected.items():
        path = joined(root, relative)
        check_path(path, kind="file")
        content = path.read_bytes()
        if digest(content) != checksum:
            raise InstallError("Pinned EGM source changed: " + relative)
        result[EGM_RUNTIME + relative] = content
    return result


def source_files(profile: str, with_improve: bool, hosts: list[str] | None = None,
                 skills: list[str] | None = None) -> dict[str, bytes]:
    """Read every selected source first, so missing packages cannot partially install."""
    hosts = selected_hosts(hosts)
    skills = selected_skills(default_skills(profile, with_improve) if skills is None else skills)
    profile = "knowledge" if "oaw-wiki" in skills else profile
    with_improve = with_improve or "oaw-improve" in skills
    source_root = framework_root()
    mappings = {"AGENTS.md": "templates/AGENTS.md", "CLAUDE.md": "templates/CLAUDE.md",
                "scripts/context_hub.py": "scripts/context_hub.py", "scripts/oaw_common.py": "scripts/oaw_common.py"}
    trees = [".agents/skills/" + name for name in skills]
    if profile == "knowledge":
        mappings.update({"scripts/wiki_sync.py": "scripts/wiki_sync.py", "scripts/validate_skills.py": "scripts/validate_skills.py"})
        trees.extend(["docs/raw", "docs/knowledge"])
    if with_improve:
        mappings["scripts/improvement.py"] = "scripts/improvement.py"
    if "claude" in hosts and any(name in EGM_SKILLS for name in skills):
        mappings.update(egm_native_agents())
    for tree in trees:
        source = joined(source_root / "templates", tree)
        check_path(source, kind="dir")
        if not source.is_dir():
            raise InstallError(f"Required source directory is missing: {source}")
        found = []
        for item in sorted(source.rglob("*")):
            check_path(item)
            if item.is_dir():
                continue
            check_path(item, kind="file")
            relative = item.relative_to(source_root / "templates").as_posix()
            if relative.startswith(".agents/skills/"):
                for host in hosts:
                    destination = relative if host == "codex" else ".claude/" + relative.removeprefix(".agents/")
                    mappings[destination] = item.relative_to(source_root).as_posix()
            else:
                mappings[relative] = item.relative_to(source_root).as_posix()
            found.append(item)
        if not found or (tree.startswith(".agents/skills/") and not (source / "SKILL.md").is_file()):
            raise InstallError(f"Required source tree is empty or lacks SKILL.md: {source}")
    files = egm_payload()
    for relative, source_relative in sorted(mappings.items()):
        relative_path(relative)
        source = joined(source_root, source_relative)
        check_path(source, kind="file")
        if not source.is_file():
            raise InstallError(f"Required source file is missing: {source}")
        files[relative] = source.read_bytes()
    return files


def legacy_hashes() -> dict[str, list[str]]:
    path = framework_root() / "scripts" / "legacy_manifest.json"
    check_path(path, kind="file")
    data = read_json(path)
    if data.get("schema_version") != 1 or not isinstance(data.get("files"), dict):
        raise InstallError("Invalid legacy manifest.")
    for relative, checksums in data["files"].items():
        relative_path(relative)
        if not isinstance(checksums, list) or not checksums or any(not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v) for v in checksums):
            raise InstallError(f"Invalid legacy hashes: {relative}")
    return data["files"]


def plan_install(target: Path, profile: str, with_improve: bool, *, migrate: bool = False,
                 keep_custom: list[str] | None = None, hosts: list[str] | None = None,
                 skills: list[str] | None = None, reset_recipe: bool = False) -> dict:
    target = target_path(target)
    manifest_path = joined(target, MANIFEST_PATH)
    check_path(manifest_path, kind="file")
    manifest_before = manifest_path.read_bytes() if manifest_path.exists() else None
    previous = read_manifest(target)
    if (manifest_path.read_bytes() if manifest_path.exists() else None) != manifest_before:
        raise InstallError("Install manifest changed during preflight; retry the command.")
    hosts = selected_hosts(hosts)
    # Additive profiles: a default re-init never drops installed optional features.
    if previous:
        profile = "knowledge" if previous["profile"] == "knowledge" else profile
        with_improve = with_improve or previous["with_improve"]
        hosts = [host for host in HOSTS if host in hosts or host in previous.get("hosts", ["codex"])]
    explicit_skills = skills is not None or bool(previous and previous.get("skills_explicit", "skills" in previous))
    if reset_recipe:
        skills, explicit_skills = None, False
    elif skills is None and explicit_skills:
        skills = previous["skills"]
    skills = selected_skills(default_skills(profile, with_improve) if skills is None else skills)
    profile = "knowledge" if "oaw-wiki" in skills else profile
    with_improve = with_improve or "oaw-improve" in skills
    package = source_files(profile, with_improve, hosts, skills=skills)
    legacy = legacy_hashes() if migrate else {}
    owned = previous["managed_files"] if previous else {}
    custom = set(previous.get("custom_files", [])) if previous else set()
    requested_custom = set(keep_custom or [])
    for relative in requested_custom:
        relative_path(relative)
    if requested_custom and not migrate:
        raise InstallError("Custom acknowledgements are only available through migrate --apply.")
    actions, managed = [], dict(owned)
    for relative, content in package.items():
        destination = joined(target, relative)
        check_path(destination, kind="file")
        before = destination.read_bytes() if destination.exists() else None
        expected, after = digest(before) if before is not None else None, digest(content)
        if relative in custom:
            operation = "preserve-custom"
            managed.pop(relative, None)
        elif relative.startswith("docs/") and before is not None:
            operation = "preserve"
            managed.pop(relative, None)
        elif before is None:
            operation = "add"
            if not relative.startswith("docs/"):
                managed[relative] = after
        elif expected == after:
            operation = "unchanged"
            managed[relative] = after
        elif owned.get(relative) == after:
            # The package is unchanged since install; keep the user's edit under the installed hash.
            operation = "preserve-edit"
        elif migrate and (owned.get(relative) == expected or expected in legacy.get(relative, [])):
            operation = "replace"
            managed[relative] = after
        else:
            operation = "conflict"
        actions.append({"path": relative, "action": operation, "before": expected, "after": after})
    # Deactivation removes only owned native entry packages, never project data.
    # Edited entrypoints block the entire package so no dangling bridge remains.
    retiring = {}
    for relative in set(owned) | custom:
        match = re.fullmatch(r"(\.(?:agents|claude)/skills/([^/]+)/).+", relative)
        if match and match.group(2) in BUNDLED_SKILLS and match.group(2) not in skills and match.group(1) + "SKILL.md" not in custom:
            retiring.setdefault(match.group(1), []).append(relative)
    if retiring and not migrate:
        raise InstallError("Changing an installed recipe can retire native packages; use migrate to preview, then --apply.")
    for prefix, relatives in retiring.items():
        entry = prefix + "SKILL.md"
        entry_path = joined(target, entry)
        if entry in custom:
            # An explicit acknowledgement retains a project-owned override,
            # including its dependent assets. Recipe selection cannot delete it.
            continue
        blocked = entry_path.is_file() and digest(entry_path.read_bytes()) != owned.get(entry)
        if blocked:
            actions.append({"path": entry, "action": "retire-conflict", "before": digest(entry_path.read_bytes()) if entry_path.is_file() else None, "after": None})
            continue
        for relative in relatives:
            destination = joined(target, relative)
            check_path(destination, kind="file")
            if not destination.exists():
                managed.pop(relative, None)
                continue
            before = digest(destination.read_bytes())
            if relative in custom or before != owned[relative]:
                actions.append({"path": relative, "action": "preserve-retired-edit", "before": before, "after": None})
                custom.add(relative)
            else:
                actions.append({"path": relative, "action": "retire", "before": before, "after": None})
            managed.pop(relative, None)
    retained_egm = any(
        re.fullmatch(r"\.(?:agents|claude)/skills/(" + "|".join(EGM_SKILLS) + r")/SKILL\.md", path)
        for path in custom | {a["path"] for a in actions if a["action"] == "retire-conflict"})
    if not any(name in EGM_SKILLS for name in skills) and not retained_egm:
        for relative in egm_native_agents():
            if relative in custom:
                continue
            if relative not in owned and relative not in custom:
                continue
            if not migrate:
                raise InstallError("Retiring native EGM agents requires migrate to preview, then --apply.")
            destination = joined(target, relative)
            check_path(destination, kind="file")
            if not destination.exists():
                managed.pop(relative, None)
                continue
            before = digest(destination.read_bytes())
            operation = "retire" if relative in owned and owned[relative] == before else "retire-conflict"
            actions.append({"path": relative, "action": operation, "before": before, "after": None})
            if operation == "retire":
                managed.pop(relative, None)
    by_path = {action["path"]: action for action in actions}
    agents, claude = by_path.get("AGENTS.md"), by_path.get("CLAUDE.md")
    # A v1 AGENTS.md only points at CLAUDE.md; keep it while a retained CLAUDE.md does not import AGENTS.md.
    if (agents and claude and agents["action"] == "replace" and owned.get("AGENTS.md") != agents["before"]
            and claude["action"] not in ("add", "replace", "unchanged")
            and not imports_agents(joined(target, "CLAUDE.md").read_bytes())):
        agents["action"] = "conflict"
        managed.pop("AGENTS.md")
        if "AGENTS.md" in owned:
            managed["AGENTS.md"] = owned["AGENTS.md"]
    for relative in requested_custom:
        action = by_path.get(relative)
        if relative not in custom and (action is None or action["action"] not in ("conflict", "preserve-edit", "retire-conflict")):
            raise InstallError(f"--keep-custom requires a current package conflict, edited managed file or declared custom path: {relative}")
        destination = joined(target, relative)
        check_path(destination, kind="file")
        if not destination.is_file():
            raise InstallError(f"Cannot acknowledge a missing custom file: {relative}")
        custom.add(relative)
        managed.pop(relative, None)
        if action is not None:
            action["action"] = "preserve-custom"
        if action and action["after"] is None and relative.endswith("/SKILL.md"):
            # Keep a retired custom entry coherent with all its owned resources.
            prefix = relative.removesuffix("SKILL.md")
            for member in list(managed):
                if member.startswith(prefix):
                    custom.add(member)
                    managed.pop(member)
    if migrate:
        for relative, hashes in sorted(legacy.items()):
            if relative in package or relative in ALWAYS_PRESERVE or relative.startswith("docs/"):
                continue
            flat_skill = relative.startswith(".agents/skills/") and relative.endswith(".md") and "/" not in relative[len(".agents/skills/"):]
            old_helper = relative == "scripts/wiki_sync.py" and profile == "minimal"
            if not (flat_skill or old_helper or relative in LEGACY_ADAPTERS):
                continue
            destination = joined(target, relative)
            check_path(destination, kind="file")
            if destination.exists():
                before = digest(destination.read_bytes())
                action = "retire" if before in hashes else "preserve"
                actions.append({"path": relative, "action": action, "before": before, "after": None})
                if action == "retire":
                    managed.pop(relative, None)
    for relative in (MANIFEST_PATH, ".oaw/install.lock"):
        check_path(joined(target, relative), kind="file")
    for relative in (".oaw/backups", ".oaw/proposals"):
        check_path(joined(target, relative), kind="dir")
    return {"target": target, "profile": profile, "with_improve": with_improve, "hosts": hosts, "previous": previous,
            "manifest_before": manifest_before,
            "skills": skills, "skills_explicit": explicit_skills,
            "package": package, "managed_files": managed, "custom_files": sorted(custom), "actions": actions}


def atomic_write(path: Path, content: bytes) -> None:
    check_path(path, kind="file")
    existing_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    check_path(path.parent, kind="dir")
    handle, temporary = tempfile.mkstemp(prefix=".oaw-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if existing_mode is not None:
            os.chmod(temporary, existing_mode)
        check_path(path, kind="file")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def json_bytes(data: dict) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


@contextmanager
def install_lock(target: Path):
    path = target / ".oaw" / "install.lock"
    check_path(path, kind="file")
    path.parent.mkdir(parents=True, exist_ok=True)
    check_path(path.parent, kind="dir")
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise InstallError(f"Another operation or stale lock exists: {path}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"pid={os.getpid()}\n")
        yield
    finally:
        path.unlink()


def apply_plan(plan: dict, *, migrate: bool) -> dict:
    target = plan["target"]
    conflicts = [a["path"] for a in plan["actions"] if a["action"] in ("conflict", "retire-conflict")]
    if conflicts and not migrate:
        raise InstallError("Existing content is protected; init made no changes. Use migrate to preview proposals: " + ", ".join(conflicts))
    operation_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    backup_relative, proposal_relative = f".oaw/backups/{operation_id}", f".oaw/proposals/{operation_id}"
    for action in plan["actions"]:
        if action["action"] in ("replace", "retire"):
            check_path(joined(target, backup_relative + "/" + action["path"]), kind="file")
        if action["action"] == "conflict":
            check_path(joined(target, proposal_relative + "/" + action["path"]), kind="file")
    previous = plan["previous"]
    manifest = {"schema_version": 1, "framework_version": FRAMEWORK_VERSION,
                "installation_id": previous.get("installation_id", uuid.uuid4().hex) if previous else uuid.uuid4().hex,
                "profile": plan["profile"], "with_improve": plan["with_improve"], "managed_files": plan["managed_files"],
                "hosts": plan["hosts"],
                "skills": plan["skills"], "skills_explicit": plan["skills_explicit"],
                "integrations": {"egm": {"commit": EGM_COMMIT, "version": "0.1.0", "source_lock_sha256": EGM_LOCK_SHA256}},
                "custom_files": plan["custom_files"],
                "runtime": {"minimum_python": "3.10", "state": "project files", "host_settings": "not configured"},
                "status": "conflicts" if conflicts else "installed", "pending_conflicts": conflicts}
    manifest_path = joined(target, MANIFEST_PATH)
    manifest_before = plan["manifest_before"]
    applied, backups, proposals = [], [], []
    target.mkdir(parents=True, exist_ok=True)
    with install_lock(target):
        for action in plan["actions"]:
            destination = joined(target, action["path"])
            check_path(destination, kind="file")
            actual = digest(destination.read_bytes()) if destination.exists() else None
            if actual != action["before"]:
                raise InstallError(f"Target changed since preflight: {action['path']}; retry the command.")
        if (manifest_path.read_bytes() if manifest_path.exists() else None) != manifest_before:
            raise InstallError("Install manifest changed since preflight; retry the command.")
        if migrate:
            for action in plan["actions"]:
                if action["action"] in ("replace", "retire"):
                    relative = backup_relative + "/" + action["path"]
                    original = joined(target, action["path"])
                    backup = joined(target, relative)
                    atomic_write(backup, original.read_bytes())
                    os.chmod(backup, stat.S_IMODE(original.stat().st_mode))
                    backups.append(relative)
            if manifest_before is not None:
                relative = backup_relative + "/install.json"
                atomic_write(joined(target, relative), manifest_before)
                backups.append(relative)
        try:
            for action in plan["actions"]:
                operation, relative = action["action"], action["path"]
                destination = joined(target, relative)
                check_path(destination, kind="file")
                if operation in ("add", "replace"):
                    atomic_write(destination, plan["package"][relative])
                    applied.append(action)
                elif operation == "retire":
                    destination.unlink()
                    applied.append(action)
                elif operation == "conflict":
                    proposal = proposal_relative + "/" + relative
                    atomic_write(joined(target, proposal), plan["package"][relative])
                    proposals.append(proposal)
            if migrate:
                receipt = {"schema_version": 1, "operation_id": operation_id, "actions": plan["actions"],
                           "backups": backups, "proposals": proposals, "previous_manifest_existed": manifest_before is not None}
                atomic_write(joined(target, backup_relative + "/migration.json"), json_bytes(receipt))
            if json_bytes(manifest) != manifest_before:
                atomic_write(manifest_path, json_bytes(manifest))
        except (OSError, InstallError) as exc:
            rollback_errors = []
            for action in reversed(applied):
                try:
                    destination = joined(target, action["path"])
                    check_path(destination, kind="file")
                    current = digest(destination.read_bytes()) if destination.exists() else None
                    if action["action"] == "add":
                        if current == action["after"]:
                            destination.unlink()
                        elif current is not None:
                            raise InstallError(f"Concurrent edit preserved during rollback: {action['path']}")
                    else:
                        if current not in (None, action["after"]):
                            raise InstallError(f"Concurrent edit preserved during rollback: {action['path']}")
                        backup = joined(target, backup_relative + "/" + action["path"])
                        atomic_write(destination, backup.read_bytes())
                        os.chmod(destination, stat.S_IMODE(backup.stat().st_mode))
                except (OSError, InstallError) as error:
                    rollback_errors.append(str(error))
            try:
                if manifest_path.exists() and manifest_path.read_bytes() == json_bytes(manifest):
                    if manifest_before is None:
                        manifest_path.unlink()
                    else:
                        atomic_write(manifest_path, manifest_before)
            except (OSError, InstallError) as error:
                rollback_errors.append(str(error))
            suffix = "; rollback issues: " + "; ".join(rollback_errors) if rollback_errors else ""
            recovery = f"recoverable backups are under {backup_relative}" if migrate else "new payload files rolled back"
            raise InstallError(f"Write failed; {recovery}: {exc}{suffix}") from exc
    return {"status": manifest["status"], "target": str(target), "profile": plan["profile"],
            "hosts": plan["hosts"],
            "skills": plan["skills"],
            "with_improve": plan["with_improve"], "actions": plan["actions"], "backup": backup_relative if migrate else None,
            "proposals": proposals, "pending_conflicts": conflicts, "custom_files": plan["custom_files"]}


def skill_issues(path: Path) -> list[str]:
    validator = framework_root() / "scripts" / "validate_skills.py"
    if validator.is_file():
        check_path(validator, kind="file")
        spec = importlib.util.spec_from_file_location("oaw_doctor_skill_validator", validator)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return list(module.lint_skill_file(path))
    # Minimal installation also remains diagnosable if the optional validator is unavailable.
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        return ["missing/unterminated YAML frontmatter"]
    fields = {}
    for line in lines[1:lines.index("---", 1)]:
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            fields[key] = value.strip().strip('"\'')
    issues = []
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", fields.get("name", "")) or fields.get("name") != path.parent.name:
        issues.append("skill name must match its directory and use lowercase hyphenated words")
    if not fields.get("description") or fields.get("description") in ("|", ">"):
        issues.append("skill description must be a nonempty scalar")
    return issues


def doctor(target: Path) -> dict:
    target = target_path(target)
    checks = []
    manifest = read_manifest(target)
    if manifest is None:
        checks.append({"status": "FAIL", "path": MANIFEST_PATH, "detail": "No OAW installation manifest; use init or migrate."})
    else:
        if manifest.get("status") != "installed" or manifest.get("pending_conflicts"):
            checks.append({"status": "FAIL", "path": MANIFEST_PATH, "detail": "Migration has unresolved conflicts."})
        native_egm = any(re.fullmatch(r"\.(?:agents|claude)/skills/(egm-[^/]+)/SKILL\.md", p)
                         for p in manifest["managed_files"])
        if "skills" in manifest or native_egm or "egm" in manifest.get("integrations", {}) or any(p.startswith(EGM_RUNTIME) for p in manifest["managed_files"]):
            try:
                egm_payload(joined(target, EGM_RUNTIME.rstrip("/")))
                checks.append({"status": "PASS", "path": EGM_RUNTIME, "detail": "Complete pinned EGM runtime and license verified."})
            except (InstallError, OSError, ValueError) as exc:
                checks.append({"status": "FAIL", "path": EGM_RUNTIME, "detail": str(exc)})
        for relative, expected in sorted(manifest["managed_files"].items()):
            path = joined(target, relative)
            if not path.is_file():
                status, detail = "FAIL", "Managed file is missing."
            elif digest(path.read_bytes()) != expected:
                status, detail = "WARN", "Modified managed file; your edit is kept, and a framework update to it becomes a migration conflict."
            else:
                status, detail = "PASS", "Managed hash matches."
            checks.append({"status": status, "path": relative, "detail": detail})
        for relative in manifest.get("custom_files", []):
            path = joined(target, relative)
            status = "PASS" if path.is_file() else "FAIL"
            detail = "Project-owned custom file; OAW will preserve it." if path.is_file() else "Declared custom file is missing."
            checks.append({"status": status, "path": relative, "detail": detail})
            selected = manifest.get("skills")
            match = re.fullmatch(r"\.(?:agents|claude)/skills/([^/]+)/SKILL\.md", relative)
            retained_skill = match and selected is not None and match.group(1) not in selected
            retained_agent = relative.startswith(".claude/agents/egm-") and selected is not None and not any(name in EGM_SKILLS for name in selected)
            if path.is_file() and (retained_skill or retained_agent):
                checks.append({"status": "WARN", "path": relative, "detail": "Explicitly retained project-owned entrypoint remains active outside the selected recipe; disable it manually before claiming an ablation."})
        required = ["AGENTS.md", "CLAUDE.md", "scripts/context_hub.py", "scripts/oaw_common.py"]
        skill_names = manifest.get("skills", ["oaw-evidence"])
        if manifest["profile"] == "knowledge":
            required.extend(["scripts/wiki_sync.py", "scripts/validate_skills.py"])
            if "skills" not in manifest:
                skill_names.append("oaw-wiki")
        if manifest["with_improve"]:
            required.append("scripts/improvement.py")
            if "skills" not in manifest:
                skill_names.append("oaw-improve")
        for host in manifest.get("hosts", ["codex"]):
            prefix = ".agents" if host == "codex" else ".claude"
            required.extend(f"{prefix}/skills/{name}/SKILL.md" for name in skill_names)
        retained_egm = any(re.fullmatch(r"\.(?:agents|claude)/skills/(" + "|".join(EGM_SKILLS) + r")/SKILL\.md", path)
                           for path in set(manifest["managed_files"]) | set(manifest.get("custom_files", [])))
        if "claude" in manifest.get("hosts", []) and (any(name in EGM_SKILLS for name in skill_names) or retained_egm):
            required.extend(egm_native_agents())
        for relative in required:
            check_path(joined(target, relative), kind="file")
            declared = relative in manifest["managed_files"] or relative in manifest.get("custom_files", [])
            if not joined(target, relative).is_file() or not declared:
                checks.append({"status": "FAIL", "path": relative, "detail": "Required policy/skill/helper is missing or unmanaged."})
        claude = joined(target, "CLAUDE.md")
        if claude.is_file() and not imports_agents(claude.read_bytes()):
            checks.append({"status": "WARN", "path": "CLAUDE.md",
                           "detail": "CLAUDE.md does not import @AGENTS.md; Claude and Codex may follow different policy."})
    if manifest:
        inventory = set(manifest["managed_files"]) | set(manifest.get("custom_files", [])) | set(required)
        for relative in sorted(inventory):
            if not re.fullmatch(r"\.(?:agents|claude)/skills/[^/]+/SKILL\.md", relative):
                continue
            path = joined(target, relative)
            check_path(path, kind="file")
            if path.is_file():
                for issue in skill_issues(path):
                    checks.append({"status": "FAIL", "path": relative, "detail": str(issue)})
    capabilities = [
        {"capability": "Third-party skill/plugin validation", "support": "HOST", "enabled": "UNKNOWN", "reason": "Doctor validates OAW's declared packages only; other packages need their host/upstream checks."},
        {"capability": "Codex AGENTS.md and native skills", "support": "YES", "enabled": "UNKNOWN", "reason": "Artifacts are packaged; host discovery/settings were not inspected."},
        {"capability": "Claude @AGENTS.md adapter and native skills", "support": "YES", "enabled": "UNKNOWN", "reason": "Adapter is packaged; host skill paths/settings were not inspected."},
        {"capability": "Sandbox, approvals, compaction, execution checkpoints", "support": "HOST", "enabled": "UNKNOWN", "reason": "Owned by the host runtime, not configured by OAW."},
    ]
    return {"status": "healthy" if not any(c["status"] == "FAIL" for c in checks) else "unhealthy",
            "target": str(target), "hosts": manifest.get("hosts", ["codex"]) if manifest else [],
            "checks": checks, "capabilities": capabilities}


def print_result(result: dict, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    print(f"OAW {result['status']}: {result['target']}")
    for skill in result.get("available_skills", []):
        enabled = ",".join(skill["installed_hosts"]) or "not selected"
        print(f"  {skill['name']:24} {skill['origin']:6} {enabled}")
    for item in result.get("actions", []):
        print(f"  {item['action']:10} {item['path']}")
    for item in result.get("checks", []):
        print(f"  {item['status']:4} {item['path']}: {item['detail']}")
    for item in result.get("capabilities", []):
        print(f"  {item['capability']}: SUPPORT={item['support']} ENABLED={item['enabled']}")
    if result.get("backup"):
        print(f"  Backup/receipt: {result['backup']}")
    for proposal in result.get("proposals", []):
        print(f"  Proposed replacement: {proposal}")
    if result.get("pending_conflicts"):
        print("  Unresolved conflicts remain; review proposals before claiming migration complete.")


def skill_inventory(target: Path | None = None) -> dict:
    egm_payload()
    manifest = read_manifest(target) if target is not None else None
    rows = []
    for name in BUNDLED_SKILLS:
        installed = []
        if target is not None:
            for host, prefix in (("codex", ".agents"), ("claude", ".claude")):
                path = joined(target, f"{prefix}/skills/{name}/SKILL.md")
                check_path(path, kind="file")
                if path.is_file():
                    installed.append(host)
        rows.append({"name": name, "origin": "EGM" if name in EGM_SKILLS else "OAW",
                     "version": "0.1.0" if name in EGM_SKILLS else FRAMEWORK_VERSION,
                     "source_commit": EGM_COMMIT if name in EGM_SKILLS else None,
                     "installed_hosts": installed})
    return {"status": "skills", "target": str(target) if target is not None else "bundled V2 skills",
            "available_skills": rows, "selected": manifest.get("skills") if manifest else None,
            "default": default_skills("minimal", False),
            "scope": "Bundled skills only. External host-native skills remain project/user owned; no global host settings changed."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("skills", help="list bundled V2 skills and a project's installed entrypoints")
    listing.add_argument("--target")
    listing.add_argument("--json", action="store_true")
    for command in ("init", "migrate", "doctor"):
        sub = commands.add_parser(command)
        sub.add_argument("--target", default=".", help="project directory (default: current directory)")
        sub.add_argument("--json", action="store_true", help="print a machine-readable result")
        if command != "doctor":
            sub.add_argument("--profile", choices=PROFILES, default="minimal")
            sub.add_argument("--host", choices=(*HOSTS, "both"), default="codex",
                             help="native skill folder(s) to install; existing hosts are retained")
            sub.add_argument("--with-improve", action="store_true", help="also install the opt-in improvement workflow")
            sub.add_argument("--skills", help="exact bundled native skill selection: comma-separated names, none, or default")
        if command == "migrate":
            sub.add_argument("--apply", action="store_true", help="apply with backups; otherwise only preview")
            sub.add_argument("--keep-custom", action="append", default=[], metavar="PATH",
                             help="with --apply, acknowledge a reviewed conflict as project-owned (repeatable)")
    args = parser.parse_args(argv)
    try:
        if sys.version_info < (3, 10):
            raise InstallError("Python 3.10+ is required.")
        if args.command == "skills":
            result = skill_inventory(target_path(args.target) if args.target else None)
            print_result(result, as_json=args.json)
            return 0
        if args.command == "migrate" and args.keep_custom and not args.apply:
            raise InstallError("--keep-custom requires --apply; dry-run never acknowledges custom content.")
        target = target_path(args.target)
        if args.command == "doctor":
            result = doctor(target)
            code = 0 if result["status"] == "healthy" else 1
        else:
            migrate = args.command == "migrate"
            selection = None if args.skills in (None, "default") else ([] if args.skills == "none" else [name.strip() for name in args.skills.split(",")])
            plan = plan_install(target, args.profile, args.with_improve, migrate=migrate,
                                keep_custom=args.keep_custom if migrate else None,
                                hosts=list(HOSTS) if args.host == "both" else [args.host],
                                skills=selection, reset_recipe=args.skills == "default")
            if migrate and not args.apply:
                result = {"status": "dry-run", "target": str(target), "profile": plan["profile"],
                          "hosts": plan["hosts"],
                          "with_improve": plan["with_improve"], "actions": plan["actions"],
                          "skills": plan["skills"],
                          "custom_files": plan["custom_files"],
                          "pending_conflicts": [a["path"] for a in plan["actions"] if a["action"] in ("conflict", "retire-conflict")]}
                code = 0
            else:
                result = apply_plan(plan, migrate=migrate)
                code = 3 if result["pending_conflicts"] else 0
        print_result(result, as_json=args.json)
        return code
    except (InstallError, OSError, UnicodeError) as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"OAW error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
