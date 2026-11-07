#!/usr/bin/env python3
"""User skill installs (plan 2.0.1 W3, owner decision D34): `oaw.py add`, `list` and `remove`.

The user decides for their own project. With consent given in the one install question, `add` may
install untasted skills, bundled scripts, hooks and MCP servers; OAW's own absorb into its defaults
keeps its blocks (catalog.py). Sources are only read: a GitHub repository through the catalog's
hardened fetch (no checkout, no hooks), a local folder byte by byte. Nothing fetched is executed,
imported or built.

Every installed part keeps a change record in .oaw/user-skills.json: each file it wrote with the
previous content's hash and a backup, and each entry it added to a shared settings file. `remove`
puts exactly those back; a file or entry the user changed since is reported and left alone.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import oaw  # noqa: E402
import catalog_core as core  # noqa: E402
import oaw_common  # noqa: E402

InstallError = oaw.InstallError
RECORD_PATH = oaw.USER_RECORD
RECORD_SCHEMA = "oaw-user-skills/1"
VERDICTS_SCHEMA = "oaw-verdicts/1"
STATE_DIR = ".oaw/user-skills"            # backups/<package>/<path> and baselines/<shared file>
SUPPORT_DIR = ".claude/oaw-user"          # files a package's hooks or MCP servers run: SUPPORT_DIR/<package>/<source path>
SETTINGS = ".claude/settings.json"
MCP_FILE = ".mcp.json"
SHARED_FILES = (SETTINGS, MCP_FILE)
WRITE_PREFIXES = (".agents/skills/", ".claude/skills/", ".claude/agents/", ".claude/commands/", SUPPORT_DIR + "/", STATE_DIR + "/")
SKILL_ROOTS = {"codex": ".agents/skills/", "claude": ".claude/skills/"}
CHOICES = ("oaw", "only", "recommended")
CHOICE_ALIASES = {"1": "oaw", "①": "oaw", "2": "only", "②": "only", "3": "recommended", "③": "recommended"}
CHOICE_ZH = {"oaw": "① OAW + 你加的 skill", "only": "② 只用你加的 skill（OAW 只當管理員）", "recommended": "③ 建議組合"}
CONSENTS = ("hooks", "mcp", "scripts")
CONSENT_ZH = {"hooks": "hook（主機在事件發生時自動執行）", "mcp": "MCP server（主機啟動時自動執行）",
              "scripts": "skill 附帶的 script（agent 照 skill 指示執行）"}
SAME_NAME_ACTIONS = ("rename", "skip", "replace")
OVERLAP_ACTIONS = ("keep-both", "use-theirs", "use-oaw")
CONTEXT_EVENTS = ("sessionstart", "userpromptsubmit", "precompact", "subagentstart")
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SERVER_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
EXIT_CHOICE = 3
TASTE_COST_ZH = "程式理解類約 2–4M token"
EXPLICIT_YAML = b"# Added by OAW: this skill runs only when you call it.\npolicy:\n  allow_implicit_invocation: false\n"
NOT_INSTALLED_ZH = {
    "instruction-file": "別人的 AGENTS.md／CLAUDE.md 不裝：專案政策由你決定",
    "docs": "說明文件不裝", "other": "設定、圖檔和其他檔案不裝", "binary": "二進位檔不裝",
    "dependency-manifest": "相依清單不裝，也不安裝相依（要用請自己裝）",
    "executable": "skill 資料夾以外、也沒被 hook 或 MCP 叫用的 script 不裝",
    "plugin-manifest": "plugin 設定檔本身不裝（裡面的 skill、hook、MCP 照上面處理）",
}


# --------------------------------------------------------------------------- small helpers

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(target: Path, relative: str) -> bytes | None:
    path = oaw.joined(target, relative)
    oaw.check_path(path, kind="file")
    return path.read_bytes() if path.is_file() else None


def _dest(target: Path, relative: str) -> Path:
    """A project path this route may write: allow-listed, confined, never through a symlink."""
    oaw.relative_path(relative)
    if core.member_path_error(relative):
        raise InstallError(f"Unsafe install path: {relative!r}")
    if not (relative.startswith(WRITE_PREFIXES) or relative in SHARED_FILES or relative == RECORD_PATH):
        raise InstallError(f"Outside the user-install boundary: {relative}")
    path = oaw.joined(target, relative)
    oaw.check_path(path, kind="file")
    confined = oaw_common.confined_path(target, *relative.split("/"))
    if os.path.normcase(confined) != os.path.normcase(str(path)):
        raise InstallError(f"Path leaves the project: {relative}")
    return path


def _write(target: Path, relative: str, data: bytes, mode: int | None = None) -> None:
    """Write through the boundary checks; a new file gets `mode` (0644 by default), an existing one keeps its mode unless `mode` is given."""
    path = _dest(target, relative)
    existed = path.exists()
    oaw.atomic_write(path, data)
    if mode is not None or not existed:
        os.chmod(path, mode if mode is not None else 0o644)


def _delete(target: Path, relative: str) -> None:
    path = _dest(target, relative)
    if path.is_file():
        path.unlink()
        oaw.prune_empty_parents(target, path)


def _json_doc(data: bytes | None, relative: str) -> dict:
    if data is None:
        return {}
    try:
        value = json.loads(data.decode("utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise InstallError(f"{relative} is not plain JSON, so OAW cannot merge into it: {exc}") from exc
    if not isinstance(value, dict):
        raise InstallError(f"{relative} is not a JSON object.")
    return value


def _json_bytes(doc: dict, like: bytes | None) -> bytes:
    """Serialize a shared settings file in the indentation the user's file already had."""
    indent = 2
    if like:
        match = re.search(rb"\n([ \t]+)\S", like)
        if match:
            indent = match.group(1).decode() if b"\t" in match.group(1) else len(match.group(1))
    return (json.dumps(doc, indent=indent, ensure_ascii=False) + "\n").encode("utf-8")


def _get(doc: dict, pointer: list):
    node = doc
    for key in pointer:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def tokens(byte_count: int) -> int:
    """A rough context estimate for frontmatter text: about four bytes per token."""
    return max(1, math.ceil(byte_count / 4)) if byte_count else 0


# --------------------------------------------------------------------------- verdicts and tasting records

def verdicts_path() -> Path:
    override = os.environ.get("OAW_VERDICTS")
    return Path(override) if override else oaw.framework_root() / "catalog" / "verdicts.json"


def load_verdicts(path: Path | None = None) -> dict:
    """The tasting results OAW ships (catalog/verdicts.json); empty when the file is absent."""
    path = Path(path) if path else verdicts_path()
    empty = {"schema": VERDICTS_SCHEMA, "categories": {}, "builtin": {}, "foods": []}
    if not path.is_file():
        return empty
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstallError(f"Cannot read the verdicts file: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != VERDICTS_SCHEMA:
        raise InstallError("Unsupported verdicts file schema.")
    categories = data.get("categories")
    if not isinstance(categories, dict) or not isinstance(data.get("builtin"), dict) or not isinstance(data.get("foods"), list):
        raise InstallError("Invalid verdicts file.")
    for name, entry in data["builtin"].items():
        if not isinstance(entry, dict) or entry.get("category") not in categories:
            raise InstallError(f"Invalid built-in category in the verdicts file: {name}")
    for food in data["foods"]:
        if (not isinstance(food, dict) or not NAME.fullmatch(str(food.get("id", ""))) or not isinstance(food.get("key"), str)
                or food.get("category") not in (None, *categories) or not isinstance(food.get("tasting"), (dict, type(None)))):
            raise InstallError("Invalid food entry in the verdicts file.")
        tasting = food.get("tasting")
        if tasting and tasting.get("outcome") not in (None, "default", "optional", "excrete"):
            raise InstallError(f"Invalid tasting outcome for {food['id']}.")
    return data


def find_verdict(verdicts: dict, *, key: str | None = None, name: str | None = None) -> dict | None:
    for food in verdicts.get("foods", []):
        if key is not None and food["key"] == key:
            return food
        if name is not None and (food["id"] == name.casefold() or str(food.get("repo", "")).split("/")[-1].casefold() == name.casefold()):
            return food
    return None


def ledger_tasting(target: Path, key: str) -> dict | None:
    """The latest tasting the project's own catalog ledger holds for this source (read-only), or None."""
    import build_verdicts
    catalog = target / ".oaw" / "catalog"
    try:
        registry = json.loads((catalog / "registry.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for fid, entry in sorted((registry.get("foods") or {}).items()):
        if (entry.get("source") or {}).get("key") != key:
            continue
        evidence = []
        folder = catalog / "evidence" / core.slug(fid)
        for path in sorted(folder.glob("*.json")) if folder.is_dir() else ():
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(value, dict):
                evidence.append(value)
        records = core.food_records(evidence, fid)
        if records["tastings"]:
            return {**build_verdicts.tasting_entry(records["tastings"][-1]), "commit": entry["source"].get("commit"), "from": "project-ledger"}
    return None


def tasting_status(target: Path, source: dict, verdicts: dict) -> dict:
    """What the records say about this source. No record means 未試吃; nothing is read from a README."""
    found = ledger_tasting(target, source["key"])
    food = find_verdict(verdicts, key=source["key"])
    if found is None and food and food.get("tasting"):
        found = {**food["tasting"], "commit": food.get("commit"), "from": "shipped-verdicts"}
    category = food.get("category") if food else None
    if not found:
        return {"status": "untasted", "category": category}
    tasted, installed = found.get("commit"), source.get("commit")
    return {"status": "tasted", "category": category, "from": found["from"], "outcome": found.get("outcome"),
            "label_zh": found["label_zh"], "date": found["date"], "conditions": found["conditions"],
            "evidence": found["evidence"], "reason_zh": found.get("reason_zh"), "tasted_commit": tasted,
            "same_version": bool(tasted and installed and tasted == installed)}


def conditions_short(conditions: dict) -> str:
    corpus = re.split(r"[(（;；,]", str(conditions.get("corpus") or ""))[0].strip()
    models = "、".join(conditions.get("models") or [])
    return "、".join(part for part in (corpus, models) if part)


def tasting_text(tasting: dict, package: str) -> str:
    if tasting["status"] != "tasted":
        return f"未試吃（試吃：catalog.py taste {package}）"
    text = f"{tasting['label_zh']}（{tasting['date']}，{conditions_short(tasting['conditions'])}）"
    if tasting.get("tasted_commit") and not tasting.get("same_version"):
        text += f"；試吃的是 {tasting['tasted_commit'][:7]}，不是你裝的版本"
    return text


# --------------------------------------------------------------------------- sources

def parse_source(text: str, verdicts: dict) -> dict:
    """A local folder, a GitHub repository (optionally URL@ref), or a name in the shipped verdicts file."""
    raw = str(text or "").strip()
    if not raw:
        raise InstallError("Empty source.")
    local = raw[7:] if raw.casefold().startswith("file://") else raw
    if os.path.isdir(local):
        path = Path(os.path.abspath(local))
        if oaw.is_path_alias(path):
            raise InstallError(f"Symlink/junction source refused: {path}")
        return {"kind": "local", "key": "file://" + path.as_posix(), "path": str(path), "owner": None, "repo": path.name,
                "display": "local/" + path.name, "url": None, "ref": None, "subdir": None, "input": raw}
    food = find_verdict(verdicts, name=raw) if not re.search(r"[/:@]", raw) else None
    if food:
        source = core.normalize_source(food["url"])
        return {**_github(source, food.get("commit")), "input": raw, "from_verdicts": food["id"]}
    url, ref = raw, None
    if "@" in raw.rsplit("/", 1)[-1] and not raw.startswith("git@") or raw.count("@") > 1:
        url, ref = raw.rsplit("@", 1)
    try:
        source = core.normalize_source(url)
    except core.SourceError as exc:
        raise InstallError(f"Not a local folder, a GitHub repository or a name in OAW's verdicts: {core.sanitize_text(raw, 80)!r}") from exc
    if source["kind"] != "github":
        raise InstallError(f"Only GitHub repositories and local folders can be added: {core.sanitize_text(raw, 80)!r}")
    if ref is not None and (not re.fullmatch(r"[A-Za-z0-9._/-]{1,200}", ref) or ref.startswith("-")):
        raise InstallError(f"Unsafe ref: {core.sanitize_text(ref, 60)!r}")
    return {**_github(source, ref or source["ref"]), "input": raw}


def _github(source: dict, ref) -> dict:
    return {"kind": "github", "key": source["key"], "owner": source["owner"], "repo": source["repo"], "path": None,
            "display": source["display"], "url": source["url"], "fetch_url": source["fetch_url"], "ref": ref,
            "subdir": source.get("subdir")}


def _local_head(root: Path) -> str | None:
    """The commit a local git checkout points at, read from .git without running git (whose config could run code)."""
    git = root / ".git"
    try:
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref = head[5:].strip()
            if not re.fullmatch(r"refs/[A-Za-z0-9._/-]+", ref) or ".." in ref:
                return None
            loose = git.joinpath(*ref.split("/"))
            if loose.is_file():
                head = loose.read_text(encoding="utf-8").strip()
            else:
                packed = (git / "packed-refs").read_text(encoding="utf-8") if (git / "packed-refs").is_file() else ""
                match = re.search(r"(?m)^([0-9a-f]{40}) " + re.escape(ref) + "$", packed)
                head = match.group(1) if match else ""
    except OSError:
        return None
    return head if re.fullmatch(r"[0-9a-f]{40}", head) else None


def read_local(root: Path) -> dict:
    """Read a local folder into memory: regular files only, symlinks recorded and never followed, catalog limits."""
    files, modes, symlinks, skipped, seen, total = {}, {}, {}, [], set(), 0
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        relative_dir = Path(directory).relative_to(root).as_posix()
        prefix = "" if relative_dir == "." else relative_dir + "/"
        kept = []
        for name in sorted(dirnames):
            if name == ".git":
                continue
            if os.path.islink(os.path.join(directory, name)):
                symlinks[prefix + name] = "(directory link, not followed)"
            else:
                kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            relative, full = prefix + name, os.path.join(directory, name)
            info = os.lstat(full)
            if stat.S_ISLNK(info.st_mode):
                symlinks[relative] = core.sanitize_text(os.readlink(full), 200)
                continue
            if not stat.S_ISREG(info.st_mode) or core.member_path_error(relative, seen):
                skipped.append(relative)
                continue
            if (info.st_size > core.LIMITS["max_file_bytes"] or len(files) >= core.LIMITS["max_files"]
                    or total + info.st_size > core.LIMITS["max_total_bytes"]):
                skipped.append(relative)
                continue
            with open(full, "rb") as handle:
                files[relative] = handle.read()
            modes[relative] = "100755" if info.st_mode & 0o111 else "100644"
            total += info.st_size
    if not files:
        raise InstallError(f"The folder has no readable files: {root}")
    return {"files": files, "modes": modes, "symlinks": symlinks, "skipped": skipped, "gitlinks": [],
            "commit": _local_head(root), "integrity": "local-read", "method": "local"}


def fetch(source: dict, target: Path) -> dict:
    """Bytes of a source in memory. GitHub goes through the catalog's hardened fetch; nothing is checked out or run."""
    if source["kind"] == "local":
        snapshot = read_local(Path(source["path"]))
    else:
        import catalog
        lab = Path(tempfile.mkdtemp(prefix="oaw-add-"))
        try:
            git, snapshot, errors = catalog.find_git(target, lab), None, []
            if git:
                try:
                    snapshot = catalog.fetch_git(git, source, source.get("ref"), lab)
                except catalog.TransportError as exc:
                    errors.append(str(exc))
            if snapshot is None:
                snapshot = catalog.fetch_codeload(source, source.get("ref"))
                snapshot["fallback_reason"] = errors[0] if errors else "git is not available"
            files, modes, skipped = catalog.seal(snapshot, source.get("subdir"))
            snapshot = {**snapshot, "files": files, "modes": modes, "skipped": skipped}
        except catalog.CatalogError as exc:
            raise InstallError(f"Cannot fetch {source['display']}: {exc}") from exc
        finally:
            catalog.rmtree(lab)
    snapshot["tree_sha256"] = core.tree_sha256({p: sha(d) for p, d in snapshot["files"].items()})
    return snapshot


# --------------------------------------------------------------------------- parts of a source

def _hook_configs(files: dict) -> dict:
    """Hook groups per config file, found the way the static scan finds them."""
    found = {}
    for path in sorted(files):
        name = PurePosixPath(path).name.casefold()
        if not name.endswith(".json"):
            continue
        config = core._json(files[path])
        if config is None:
            continue
        plugin = name in ("plugin.json", "marketplace.json") or ".claude-plugin" in path or ".codex-plugin" in path
        if not (name == "hooks.json" or (name.startswith("settings") and ".claude/" in path) or (plugin and isinstance(config.get("hooks"), dict))):
            continue
        hooks = config.get("hooks", config)
        groups = {}
        if isinstance(hooks, dict):
            for event, entries in hooks.items():
                if isinstance(entries, list):
                    kept = [copy.deepcopy(g) for g in entries if isinstance(g, dict)]
                    if kept:
                        groups[str(event)] = kept
        if groups:
            ignored = sorted(k for k in config if k not in ("hooks", "mcpServers", "description")) if "hooks" in config else []
            found[path] = {"groups": groups, "ignored": ignored}
    return found


def _mcp_configs(files: dict) -> dict:
    """MCP server specs per name, found the way the static scan finds them."""
    found = {}
    for path in sorted(files):
        name = PurePosixPath(path).name.casefold()
        if not name.endswith(".json"):
            continue
        config = core._json(files[path])
        if config is None or not isinstance(config.get("mcpServers"), dict):
            continue
        plugin = name in ("plugin.json", "marketplace.json") or ".claude-plugin" in path or ".codex-plugin" in path
        if name in (".mcp.json", "mcp.json") or plugin or name.endswith("settings.json"):
            for server, spec in config["mcpServers"].items():
                found.setdefault(core.sanitize_text(server, 64), (path, str(server), copy.deepcopy(spec) if isinstance(spec, dict) else {}))
    return found


_TOKEN = re.compile(r"[\w${}.@%/\\:-]+\.(?:sh|bash|py|js|mjs|cjs|ts|ps1|bat|cmd|rb|pl)\b")
_PLUGIN_ROOT = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}|\$CLAUDE_PLUGIN_ROOT\b")


def support_root(package: str) -> str:
    return "${CLAUDE_PROJECT_DIR:-.}/" + SUPPORT_DIR + "/" + package


def rewrite_command(command: str, root: str, paths) -> str:
    """Point a hook or MCP command at the package's installed copy of the files it names. Nothing else changes."""
    def token(match):
        text = match.group(0)
        stripped = re.sub(r"^(?:\$\{[^}]+\}|\$[A-Za-z_]+|%[^%]+%)[/\\]?", "", text).replace("\\", "/")
        while stripped.startswith("./"):
            stripped = stripped[2:]
        hits = [p for p in paths if p == stripped or p.endswith("/" + stripped)]
        return f"{root}/{hits[0]}" if len(hits) == 1 else text
    return _PLUGIN_ROOT.sub(root, _TOKEN.sub(token, command))


def _rewrite_value(value, root: str, paths):
    if isinstance(value, str):
        return rewrite_command(value, root, paths)
    if isinstance(value, list):
        return [_rewrite_value(item, root, paths) for item in value]
    if isinstance(value, dict):
        return {key: (_rewrite_value(item, root, paths) if key in ("command", "args", "cwd", "env", "hooks") else item)
                for key, item in value.items()}
    return value


def build_parts(package: str, snapshot: dict, scan: dict) -> tuple[list, list]:
    """Installable parts (skills, agents, commands, hook sets, MCP servers) and what is left out, with why."""
    files, modes = snapshot["files"], snapshot["modes"]
    flags = {f["id"]: f for f in scan["flags"]}
    hook_configs, mcp_configs = _hook_configs(files), _mcp_configs(files)
    support = sorted({p for c in scan["components"] if c["kind"] in ("hook-set", "mcp-server") for p in c["paths"]
                      if p not in hook_configs and p not in {v[0] for v in mcp_configs.values()}})
    root = support_root(package)
    parts, left_out, hook_sets = [], [], 0
    for component in scan["components"]:
        kind = component["kind"]
        background = any(flags.get(fid, {}).get("allergen") == "background-process" for fid in component.get("flag_ids", []))
        base = {"part": component["id"], "background": background, "renamed_from": None, "explicit_only": False}
        if kind == "skill":
            facts = component["skill"]
            name = facts["name"] if facts["valid_name"] else core.slug(PurePosixPath(facts["dir"]).name or package)
            if not NAME.fullmatch(name):
                left_out.append({"part": component["id"], "kind": kind, "files": component["file_count"], "reason": "skill 名稱不合規則"})
                continue
            directory = facts["dir"]
            members = {m: (m[len(directory) + 1:] if directory else m) for m in component["paths"]}
            scripts = sorted(m for m in members if core.file_role(m, files[m], modes.get(m)) in ("executable", "manifest", "binary"))
            fields, _body = core.parse_frontmatter(files[facts["path"]].decode("utf-8", "replace"))
            parts.append({**base, "kind": "skill", "name": name, "members": members, "scripts": scripts,
                          "needs": ["scripts"] if scripts else [],
                          "explicit_only": str(fields.get("disable-model-invocation", "")).casefold() == "true",
                          "description_bytes": facts["description_bytes"] + facts["name_bytes"]})
        elif kind in ("agent", "command"):
            path = component["paths"][0]
            name = core.slug(PurePosixPath(path).stem)
            fields, _body = core.parse_frontmatter(files[path].decode("utf-8", "replace"))
            parts.append({**base, "kind": kind, "name": name, "members": {path: name + ".md"}, "scripts": [], "needs": [],
                          "description_bytes": len(str(fields.get("description", "")).encode("utf-8"))})
        elif kind == "hook-set":
            config = next((p for p in component["paths"] if p in hook_configs), None)
            if config is None:
                left_out.append({"part": component["id"], "kind": kind, "files": component["file_count"], "reason": "hook 設定讀不懂"})
                continue
            hook_sets += 1
            groups = {event: [_rewrite_value(g, root, support) for g in entries] for event, entries in hook_configs[config]["groups"].items()}
            parts.append({**base, "kind": "hooks", "name": f"{package}-hooks" + (f"-{hook_sets}" if hook_sets > 1 else ""),
                          "config": config, "groups": groups, "ignored_keys": hook_configs[config]["ignored"],
                          "members": {p: p for p in component["paths"] if p != config}, "scripts": [], "needs": ["hooks"]})
        elif kind == "mcp-server":
            found = mcp_configs.get(component["name"])
            if found is None or not SERVER_NAME.fullmatch(found[1]):
                left_out.append({"part": component["id"], "kind": kind, "files": component["file_count"], "reason": "MCP 設定讀不懂或名稱不合規則"})
                continue
            config, server, spec = found
            parts.append({**base, "kind": "mcp", "name": server, "config": config, "spec": _rewrite_value(spec, root, support),
                          "remote": bool(spec.get("url")), "members": {p: p for p in component["paths"] if p != config},
                          "scripts": [], "needs": ["mcp"]})
        else:
            left_out.append({"part": component["id"], "kind": kind, "files": component["file_count"],
                             "reason": NOT_INSTALLED_ZH.get(kind, "不是可以安裝的部分")})
    return parts, left_out


def _frontmatter_edit(data: bytes, *, name: str | None, explicit: bool) -> bytes:
    """Rename a skill/agent in its frontmatter, or mark it explicit-only. Other bytes stay as they were."""
    text = data.decode("utf-8")
    match = re.match(r"(﻿?---[ \t]*\r?\n)(.*?)(\r?\n---[ \t]*(?:\r?\n|$))", text, re.S)
    if not match:
        if not explicit and name is None:
            return data
        front = (f"name: {name}\n" if name else "") + ("disable-model-invocation: true\n" if explicit else "")
        return ("---\n" + front + "---\n" + text).encode("utf-8")
    head, body, tail = match.group(1), match.group(2), match.group(3)
    if name is not None:
        if re.search(r"(?m)^name:", body):
            body = re.sub(r"(?m)^name:.*$", f"name: {name}", body, count=1)
        else:
            body = f"name: {name}\n" + body
    if explicit and not re.search(r"(?mi)^disable-model-invocation:\s*true\s*$", body):
        body = re.sub(r"(?mi)^disable-model-invocation:.*\n?", "", body).rstrip("\r\n") + "\ndisable-model-invocation: true"
    return (head + body + tail + text[match.end():]).encode("utf-8")


def part_files(part: dict, package: str, hosts: list, files: dict, modes: dict) -> dict:
    """Project path -> (bytes, mode) that one part writes."""
    out, renamed = {}, part["renamed_from"] is not None
    if part["kind"] == "skill":
        for host in hosts:
            prefix = SKILL_ROOTS[host] + part["name"] + "/"
            for source, inner in part["members"].items():
                data = files[source]
                if inner == "SKILL.md" and (renamed or part["explicit_only"]):
                    data = _frontmatter_edit(data, name=part["name"] if renamed else None, explicit=part["explicit_only"])
                out[prefix + inner] = (data, 0o755 if modes.get(source) == "100755" else 0o644)
            if part["explicit_only"] and host == "codex" and "agents/openai.yaml" not in part["members"].values():
                out[prefix + "agents/openai.yaml"] = (EXPLICIT_YAML, 0o644)
    elif part["kind"] in ("agent", "command"):
        folder = ".claude/agents/" if part["kind"] == "agent" else ".claude/commands/"
        for source in part["members"]:
            data = files[source]
            if renamed:
                data = _frontmatter_edit(data, name=part["name"], explicit=False)
            out[folder + part["name"] + ".md"] = (data, 0o644)
    else:
        for source in part["members"]:
            out[f"{SUPPORT_DIR}/{package}/{source}"] = (files[source], 0o755 if modes.get(source) == "100755" else 0o644)
    return out


# --------------------------------------------------------------------------- record

def empty_record() -> dict:
    return {"schema": RECORD_SCHEMA, "packages": {}, "shared": {}}


def load_record(target: Path) -> dict:
    data = _read(target, RECORD_PATH)
    if data is None:
        return empty_record()
    try:
        record = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise InstallError(f"Cannot read {RECORD_PATH}: {exc}") from exc
    if not isinstance(record, dict) or record.get("schema") != RECORD_SCHEMA or not isinstance(record.get("packages"), dict):
        raise InstallError(f"Unsupported or invalid {RECORD_PATH}.")
    record.setdefault("shared", {})
    for package, entry in record["packages"].items():
        if not NAME.fullmatch(package) or not isinstance(entry.get("parts"), dict):
            raise InstallError(f"Invalid package in {RECORD_PATH}: {package!r}")
        for part in entry["parts"].values():
            for item in part.get("files", []):
                oaw.relative_path(item["path"])
                if not item["path"].startswith(WRITE_PREFIXES) or (item.get("backup") and not item["backup"].startswith(STATE_DIR + "/")):
                    raise InstallError(f"Record names a path outside the user-install boundary: {item['path']}")
            for entry_ in part.get("entries", []):
                if entry_.get("file") not in SHARED_FILES:
                    raise InstallError("Record names an unknown shared settings file.")
    for relative, baseline in record["shared"].items():
        if relative not in SHARED_FILES or (baseline.get("backup") and not baseline["backup"].startswith(STATE_DIR + "/")):
            raise InstallError("Record names an unknown shared settings baseline.")
    return record


def record_bytes(record: dict) -> bytes:
    return (json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def owner_in_record(record: dict, path_or_prefix: str) -> str | None:
    for package, entry in record["packages"].items():
        for part in entry["parts"].values():
            if any(f["path"] == path_or_prefix or f["path"].startswith(path_or_prefix) for f in part.get("files", []) if f.get("sha256")):
                return package
    return None


# --------------------------------------------------------------------------- the OAW side of a choice

def project_state(manifest: dict | None) -> str:
    return "clean" if manifest is None else ("only" if manifest["profile"] == oaw.MANAGER_ONLY else "oaw")


def plan_oaw_step(target: Path, manifest: dict | None, choice: str, hosts: list, retire: set) -> dict:
    """What a choice changes in OAW's own install: nothing, an init, a switch to manager-only, or retiring skills."""
    state = project_state(manifest)
    step = {"kind": "none", "plan": None, "actions": [], "skills": list(manifest.get("skills", [])) if state == "oaw" else [],
            "blocked": None}
    if choice == "only":
        if state == "only":
            return step
        plan = oaw.plan_manager_only(target, migrate=True, hosts=hosts)
        step.update(kind="manager-only", plan=plan, skills=[])
    elif state in ("clean", "only"):
        skills = [name for name in oaw.default_skills("minimal", False) if name not in retire]
        plan = oaw.plan_install(target, "minimal", False, hosts=hosts, skills=skills if retire else None)
        step.update(kind="init", plan=plan, skills=plan["skills"])
        blocked = [a["path"] for a in plan["actions"] if a["action"] == "conflict"]
        if blocked:
            step["blocked"] = ("OAW's install would meet different existing files (" + ", ".join(blocked[:5])
                               + "); preview `oaw.py migrate` for this project first.")
    elif retire & set(current := manifest.get("skills", oaw.default_skills(manifest["profile"], manifest["with_improve"]))) or (
            set(hosts) - set(manifest.get("hosts", ["codex"]))):
        selection = [name for name in current if name not in retire]
        plan = oaw.plan_install(target, manifest["profile"], manifest["with_improve"], migrate=True, hosts=hosts, skills=selection)
        step.update(kind="retire" if retire else "hosts", plan=plan, skills=plan["skills"])
        unexpected = [a for a in plan["actions"] if a["action"] not in ("unchanged", "preserve", "preserve-custom", "preserve-edit",
                                                                        "retire", "add", "preserve-retired-edit")]
        unexpected += [a for a in plan["actions"] if a["action"] == "add" and not a["path"].startswith((".claude/", ".agents/"))]
        if unexpected:
            step["blocked"] = ("OAW's install has pending changes (" + ", ".join(a["path"] for a in unexpected[:5])
                               + "); run `oaw.py migrate` first.")
    else:
        return step
    step["actions"] = [a for a in step["plan"]["actions"] if a["action"] not in ("unchanged", "preserve")]
    return step


def run_oaw_step(step: dict) -> dict | None:
    if step["kind"] == "none":
        return None
    if step["blocked"]:
        raise InstallError(step["blocked"])
    # Retiring files always goes through migrate's backups; a first install or a bare manifest does not need them.
    return oaw.apply_plan(step["plan"], migrate=any(a["action"] == "retire" for a in step["plan"]["actions"])
                          or (step["kind"] != "init" and step["plan"]["previous"] is not None))


def future_files(target: Path, manifest: dict | None, step: dict) -> tuple[set, set]:
    """Files under the host folders after the OAW step, and which of them OAW will own."""
    present = set()
    for top in (".agents/skills", ".claude/skills", ".claude/agents", ".claude/commands"):
        root = oaw.joined(target, top)
        oaw.check_path(root)
        if root.is_dir():
            for path in root.rglob("*"):
                if path.is_file() or path.is_symlink():
                    present.add(path.relative_to(target).as_posix())
    managed = set(manifest["managed_files"]) if manifest else set()
    if step["plan"] is not None:
        for action in step["plan"]["actions"]:
            if action["action"] == "add":
                present.add(action["path"])
            elif action["action"] == "retire":
                present.discard(action["path"])
        managed = set(step["plan"]["managed_files"])
    return present, managed


# --------------------------------------------------------------------------- planning `add`

def _decisions(values) -> dict:
    """--on-conflict NAME=ACTION values -> {name: {"same-name"|"overlap": action}}."""
    result = {}
    for value in values or ():
        name, _sep, action = str(value).partition("=")
        name, action = name.strip(), action.strip()
        family = "overlap" if action in OVERLAP_ACTIONS else "same-name"
        new = None
        if action.startswith("rename:"):
            action, new = "rename", action[7:]
            if not NAME.fullmatch(new) and not SERVER_NAME.fullmatch(new):
                raise InstallError(f"Invalid new name in --on-conflict {value!r}.")
        if not name or action not in (*SAME_NAME_ACTIONS, *OVERLAP_ACTIONS):
            raise InstallError(f"--on-conflict takes NAME=ACTION with ACTION in {', '.join((*SAME_NAME_ACTIONS, *OVERLAP_ACTIONS))}: {value!r}")
        result.setdefault(name, {})[family] = (action, new) if family == "same-name" else action
    return result


def _consents(value) -> set | None:
    if value is None:
        return None
    chosen = {item.strip() for item in str(value).split(",") if item.strip()}
    if chosen == {"all"}:
        return set(CONSENTS)
    if chosen == {"none"}:
        return set()
    unknown = chosen - set(CONSENTS)
    if unknown:
        raise InstallError(f"--consent takes {', '.join(CONSENTS)}, all or none; unknown: {', '.join(sorted(unknown))}")
    return chosen


def _resolve_hosts(manifest: dict | None, host: str | None) -> list:
    wanted = list(oaw.HOSTS) if host == "both" else ([host] if host else [])
    have = manifest.get("hosts", ["codex"]) if manifest else []
    return oaw.selected_hosts([h for h in oaw.HOSTS if h in wanted or h in have] or ["codex"])


def recommend(tasting: dict) -> tuple[str, str]:
    """Choice 3, deterministic: (install | explicit | skip, one line of reason) from the tasting records only."""
    if tasting["status"] != "tasted":
        return "install", "沒有試吃紀錄：照裝，清單上標「未試吃」"
    where = conditions_short(tasting["conditions"])
    outcome = tasting.get("outcome")
    if not tasting.get("same_version") and tasting.get("tasted_commit"):
        where += f"；試吃的是 {tasting['tasted_commit'][:7]}"
    if outcome == "default":
        return "install", f"試吃結果「{tasting['label_zh']}」（{where}）：照裝"
    if outcome == "optional":
        return "explicit", f"試吃結果「{tasting['label_zh']}」（{where}）：裝上，但只在你叫它時用"
    return "skip", f"不建議：{tasting['label_zh']}（在 {where} 試的）"


def plan_add(target, sources, *, choice=None, consent=None, on_conflict=(), host=None, interactive_defaults=False,
             verdicts=None, snapshots=None, retire_hint=None) -> dict:
    """Everything `add` would do, computed without writing. `snapshots` caches fetched sources by key."""
    target = oaw.target_path(target)
    manifest = oaw.read_manifest(target)
    record = load_record(target)
    verdicts = verdicts if verdicts is not None else load_verdicts()
    state = project_state(manifest)
    default_choice = "only" if state == "only" else "oaw"
    choice = choice or default_choice
    if choice not in CHOICES:
        raise InstallError(f"--choice takes {', '.join(CHOICES)}.")
    consents = _consents(consent) if not isinstance(consent, set) else consent
    decisions = _decisions(on_conflict) if not isinstance(on_conflict, dict) else on_conflict
    use_defaults = interactive_defaults or choice == "recommended"
    hosts = _resolve_hosts(manifest, host)
    snapshots = {} if snapshots is None else snapshots
    taken = {name: entry["source"]["key"] for name, entry in record["packages"].items()}
    installed_keys = {entry["source"]["key"]: name for name, entry in record["packages"].items()}
    packages, seen = [], set()
    for text in sources:
        source = parse_source(text, verdicts)
        if source["key"] in seen:
            continue
        seen.add(source["key"])
        if source["key"] not in snapshots:
            snapshots[source["key"]] = fetch(source, target)
        snapshot = snapshots[source["key"]]
        source["commit"] = snapshot.get("commit")
        source["tree_sha256"] = snapshot["tree_sha256"]
        name = core.food_id({"repo": source["repo"], "owner": source["owner"] or "local", "key": source["key"]}, taken)
        taken[name] = source["key"]
        scan = core.static_scan(snapshot["files"], food=name, commit=snapshot.get("commit"), integrity=snapshot["integrity"],
                                modes=snapshot["modes"], skipped=snapshot["skipped"], symlinks=snapshot["symlinks"],
                                gitlinks=snapshot.get("gitlinks", []))
        parts, left_out = build_parts(name, snapshot, scan)
        tasting = tasting_status(target, source, verdicts)
        package = {"name": name, "source": source, "tasting": tasting, "category": tasting["category"], "parts": parts,
                   "left_out": left_out, "license": scan["license"], "exec_class": scan["exec_class"],
                   "dependencies": scan["dependencies"]["non_stdlib"][:20], "flags": len(scan["flags"]),
                   "allergens": scan["allergens"], "skipped_files": len(snapshot["skipped"]), "symlinks": len(snapshot["symlinks"]),
                   "status": "install", "reason": None, "recommendation": None}
        if source["key"] in installed_keys:
            package.update(status="skip", reason=f"已經裝過（{installed_keys[source['key']]}）；要重裝先 oaw.py remove {installed_keys[source['key']]}")
        if not parts and package["status"] == "install":
            package.update(status="skip", reason="沒有可以安裝的 skill、agent、hook 或 MCP server")
        if choice == "recommended" and package["status"] == "install":
            action, reason = recommend(tasting)
            package["recommendation"] = {"action": action, "reason": reason}
            if action == "skip":
                package.update(status="skip", reason=reason)
            elif action == "explicit":
                for part in parts:
                    if part["kind"] == "skill":
                        part["explicit_only"] = True
        packages.append(package)

    # Overlaps with OAW's own skills of the same category (declared in verdicts.json; no semantic analysis).
    builtin_categories = {name: entry["category"] for name, entry in verdicts.get("builtin", {}).items()}
    if choice == "only":
        oaw_skills = set()
    elif state == "oaw":
        oaw_skills = set(manifest.get("skills", oaw.default_skills(manifest["profile"], manifest["with_improve"])))
    else:
        oaw_skills = set(oaw.default_skills("minimal", False))
    conflicts, retire = [], set(retire_hint or ())
    for package in packages:
        if package["status"] != "install" or not package["category"]:
            continue
        same = sorted(n for n in oaw_skills if builtin_categories.get(n) == package["category"])
        if not same:
            continue
        decision = decisions.get(package["name"], {}).get("overlap") or ("keep-both" if use_defaults else None)
        label = verdicts.get("categories", {}).get(package["category"], package["category"])
        conflicts.append({"type": "overlap", "subject": package["name"], "with": same, "category": package["category"],
                          "text": f"{package['name']} 和 OAW 的 {'、'.join(same)} 同類（{label}）",
                          "options": list(OVERLAP_ACTIONS), "decision": decision})
        if decision == "use-oaw":
            package.update(status="skip", reason=f"和 OAW 的 {'、'.join(same)} 同類，你選了用 OAW 的")
        elif decision == "use-theirs":
            retire.update(same)
    step = plan_oaw_step(target, manifest, choice, hosts, retire)
    present, managed = future_files(target, manifest, step)

    # Same names, same files, shared settings: structural checks only.
    notes, claimed = [], {}
    settings_now = _read(target, SETTINGS)
    mcp_now = _read(target, MCP_FILE)
    shared_errors = {}
    for relative, data in ((SETTINGS, settings_now), (MCP_FILE, mcp_now)):
        try:
            _json_doc(data, relative)
        except InstallError as exc:
            shared_errors[relative] = str(exc)
    settings_doc = _json_doc(settings_now, SETTINGS) if SETTINGS not in shared_errors else {}
    mcp_doc = _json_doc(mcp_now, MCP_FILE) if MCP_FILE not in shared_errors else {}
    existing_servers = set((mcp_doc.get("mcpServers") or {}) if isinstance(mcp_doc.get("mcpServers"), dict) else ())
    event_counts = {}
    if isinstance(settings_doc.get("hooks"), dict):
        for event, groups in settings_doc["hooks"].items():
            event_counts[event] = len(groups) if isinstance(groups, list) else 0
    servers_planned = set()

    def owner(prefix: str, *, is_dir: bool) -> str | None:
        user = owner_in_record(record, prefix)
        if user:
            return "user:" + user
        if prefix in claimed:
            return "batch:" + claimed[prefix]
        hits = [p for p in present if (p.startswith(prefix) if is_dir else p == prefix)]
        if any(p in managed for p in hits):
            return "oaw"
        return "project" if hits else None

    def destinations(part: dict) -> list:
        if part["kind"] == "skill":
            return [(SKILL_ROOTS[h] + part["name"] + "/", True) for h in hosts]
        if part["kind"] in ("agent", "command"):
            folder = ".claude/agents/" if part["kind"] == "agent" else ".claude/commands/"
            return [(folder + part["name"] + ".md", False)]
        return []

    def taken_name(part: dict, name: str) -> bool:
        trial = {**part, "name": name}
        if part["kind"] == "mcp":
            return name in existing_servers or name in servers_planned
        return any(owner(prefix, is_dir=is_dir) for prefix, is_dir in destinations(trial))

    owner_zh = {"oaw": "OAW 內建", "project": "專案原本就有"}
    for package in packages:
        for part in package["parts"]:
            part["status"], part["reason"], part["replace"] = "install", None, []
            if package["status"] != "install":
                part["status"], part["reason"] = "skip", package["reason"]
                continue
            if part["kind"] == "mcp":
                user = _server_owner(record, part["name"]) if part["name"] in existing_servers else None
                who = ("user:" + user if user else "project") if part["name"] in existing_servers else (
                    "batch:" + part["name"] if part["name"] in servers_planned else None)
            else:
                who = next((w for w in (owner(prefix, is_dir=is_dir) for prefix, is_dir in destinations(part)) if w), None)
            if who:
                options = [a for a in SAME_NAME_ACTIONS if a != "replace" or not who.startswith(("user:", "batch"))]
                chosen = decisions.get(part["name"], {}).get("same-name")
                if chosen and chosen[0] not in options:
                    raise InstallError(f"{part['name']}: {chosen[0]} is not possible here; choose {' or '.join(options)}.")
                if not chosen and use_defaults:
                    chosen = ("rename", None)
                described = owner_zh.get(who) or (f"你之前加的 {who[5:]}" if who.startswith("user:") else "這次一起加的另一份")
                conflicts.append({"type": "same-name", "subject": part["name"], "kind": part["kind"], "owner": who,
                                  "text": f"{package['name']} 的 {part['kind']} {part['name']} 和{described}的 {part['name']} 同名", "options": options,
                                  "decision": chosen[0] if chosen else None})
                if not chosen:
                    part["status"], part["reason"] = "needs-decision", "同名，要你選 rename、skip 或 replace"
                elif chosen[0] == "skip":
                    part["status"], part["reason"] = "skip", "同名，你選了跳過"
                elif chosen[0] == "rename":
                    new = chosen[1]
                    if new is None:
                        number = 2
                        while taken_name(part, f"{part['name']}-{number}"):
                            number += 1
                        new = f"{part['name']}-{number}"
                    elif taken_name(part, new):
                        raise InstallError(f"{part['name']}: the new name {new} is also taken.")
                    part["renamed_from"], part["name"] = part["name"], new
                else:
                    part["replace"] = [prefix for prefix, _d in destinations(part)] or ([part["name"]] if part["kind"] == "mcp" else [])
            if part["status"] == "install":
                for prefix, _is_dir in destinations(part):
                    claimed[prefix] = package["name"]
                if part["kind"] == "mcp":
                    servers_planned.add(part["name"])
            # Consent for anything that runs on its own (D34).
            missing = [need for need in part["needs"] if consents is None or need not in consents]
            if part["status"] == "install" and missing:
                if consents is None:
                    part["status"], part["reason"] = "needs-consent", "要你同意：" + "、".join(missing)
                else:
                    part["status"], part["reason"] = "skip", "沒有同意：" + "、".join(missing)
            shared = SETTINGS if part["kind"] == "hooks" else MCP_FILE if part["kind"] == "mcp" else None
            if part["status"] in ("install", "needs-consent") and shared in shared_errors:
                part["status"], part["reason"] = "blocked", shared_errors[shared]

    # Files the parts write; a second writer of one path is a conflict that is never resolved silently.
    writers = {}
    for package in packages:
        files, modes = snapshots[package["source"]["key"]]["files"], snapshots[package["source"]["key"]]["modes"]
        for part in package["parts"]:
            part["writes"] = (part_files(part, package["name"], hosts, files, modes)
                              if part["status"] in ("install", "needs-consent", "needs-decision") else {})
            if part["status"] != "install":
                continue
            clash = next((path for path in part["writes"] if path in writers), None)
            if clash:
                part["status"], part["reason"] = "blocked", f"和 {writers[clash]} 寫同一個檔案 {clash}"
                continue
            writers.update({path: f"{package['name']}/{part['name']}" for path in part["writes"]})
    events = {}
    for package in packages:
        for part in package["parts"]:
            if part["kind"] == "hooks" and part["status"] in ("install", "needs-consent"):
                for event in part["groups"]:
                    events.setdefault(event, []).append(part["name"])
    for event, names in sorted(events.items()):
        total = event_counts.get(event, 0) + len(names)
        if total > 1:
            notes.append(f"{event} 會有 {total} 個 hook（{'、'.join(names)} 加上原本的 {event_counts.get(event, 0)} 個），每次都會依序執行")
    servers = existing_servers | servers_planned
    if len(servers) > 1 and servers_planned:
        notes.append(f"專案會有 {len(servers)} 個 MCP server（{'、'.join(sorted(servers))}），每個都在主機啟動時執行並載入工具清單")
    for package in packages:
        if package["status"] == "install" and package["category"]:
            others = [p["name"] for p in packages if p is not package and p["status"] == "install" and p["category"] == package["category"]]
            others += [n for n, e in record["packages"].items() if e.get("category") == package["category"]]
            if others:
                notes.append(f"{package['name']} 和 {'、'.join(sorted(set(others)))} 同類（{package['category']}），兩個都會裝")
    open_conflicts = [c for c in conflicts if c["decision"] is None]
    consent_needed = {}
    for package in packages:
        for part in package["parts"]:
            if part["status"] == "needs-consent":
                for need in part["needs"]:
                    consent_needed.setdefault(need, []).append(part)
    return {"target": target, "manifest": manifest, "record": record, "state": state, "choice": choice,
            "default_choice": default_choice, "hosts": hosts, "packages": packages, "conflicts": conflicts,
            "open_conflicts": open_conflicts, "consent_needed": consent_needed, "consents": consents,
            "notes": notes, "oaw_step": step, "retire": sorted(retire), "snapshots": snapshots, "verdicts": verdicts}


def _server_owner(record: dict, server: str) -> str | None:
    for package, entry in record["packages"].items():
        for part in entry["parts"].values():
            if any(e["file"] == MCP_FILE and e["pointer"] == ["mcpServers", server] for e in part.get("entries", [])):
                return package
    return None


# --------------------------------------------------------------------------- applying `add`

def _shared_entries(part: dict) -> list:
    if part["kind"] == "hooks":
        return [{"file": SETTINGS, "pointer": ["hooks", event], "op": "append", "value": group}
                for event, groups in part["groups"].items() for group in groups]
    if part["kind"] == "mcp":
        return [{"file": MCP_FILE, "pointer": ["mcpServers", part["name"]], "op": "set", "value": part["spec"]}]
    return []


def commit_parts(target: Path, plan: dict) -> dict:
    """Write every part to install with its change record, under OAW's install lock. All or nothing."""
    installing = [(package, part) for package in plan["packages"] for part in package["parts"] if part["status"] == "install"]
    undo, stamp = [], now_iso()
    with oaw.install_lock(target):
        record = load_record(target)
        if record_bytes(record) != record_bytes(plan["record"]):
            raise InstallError(f"{RECORD_PATH} changed since the preview; run the command again.")
        # Shared files are parsed only when a part merges into them; one that is not plain JSON blocked that part already.
        originals = {relative: _read(target, relative) for relative in SHARED_FILES}
        docs = {}
        try:
            for package, part in installing:
                entry = record["packages"].setdefault(package["name"], _package_record(package, plan, stamp))
                files_record = []
                deletes = set()
                for prefix in part["replace"]:
                    if prefix.endswith("/"):
                        root = oaw.joined(target, prefix.rstrip("/"))
                        oaw.check_path(root)
                        if root.is_dir():
                            deletes |= {p.relative_to(target).as_posix() for p in root.rglob("*") if p.is_file()} - set(part["writes"])
                for relative in sorted(set(part["writes"]) | deletes):
                    before = _read(target, relative)
                    backup = None
                    if before is not None:
                        backup = f"{STATE_DIR}/backups/{package['name']}/{relative}"
                        mode = stat.S_IMODE(oaw.joined(target, relative).stat().st_mode)
                        undo.append((backup, _read(target, backup), None))
                        _write(target, backup, before, mode)
                        undo.append((relative, before, mode))
                    else:
                        undo.append((relative, None, None))
                    if relative in part["writes"]:
                        data, mode = part["writes"][relative]
                        _write(target, relative, data, mode)
                        files_record.append({"path": relative, "sha256": sha(data), "mode": oct(mode), "previous_sha256": sha(before) if before is not None else None,
                                             "backup": backup})
                    else:
                        _delete(target, relative)
                        files_record.append({"path": relative, "sha256": None, "previous_sha256": sha(before), "backup": backup})
                entries = []
                for item in _shared_entries(part):
                    relative = item["file"]
                    if relative not in record["shared"]:
                        baseline = None
                        if originals[relative] is not None:
                            baseline = f"{STATE_DIR}/baselines/{relative}"
                            undo.append((baseline, _read(target, baseline), None))
                            _write(target, baseline, originals[relative])
                        record["shared"][relative] = {"existed": originals[relative] is not None, "backup": baseline,
                                                      "sha256": sha(originals[relative]) if originals[relative] is not None else None}
                    if relative not in docs:
                        docs[relative] = _json_doc(originals[relative], relative)
                    doc, (*parents, key) = docs[relative], item["pointer"]
                    node = doc
                    for name in parents:
                        node = node.setdefault(name, {})
                        if not isinstance(node, dict):
                            raise InstallError(f"{relative}: {'.'.join(parents)} is not an object; nothing was merged.")
                    if item["op"] == "append":
                        container = node.setdefault(key, [])
                        if not isinstance(container, list):
                            raise InstallError(f"{relative}: {'.'.join(item['pointer'])} is not a list; nothing was merged.")
                        container.append(copy.deepcopy(item["value"]))
                    else:
                        item["previous"] = copy.deepcopy(node.get(key))
                        item["had_previous"] = key in node
                        node[key] = copy.deepcopy(item["value"])
                    entries.append(item)
                entry["parts"][part["name"]] = {
                    "name": part["name"], "kind": part["kind"], "renamed_from": part["renamed_from"],
                    "explicit_only": part["explicit_only"], "needs": part["needs"], "scripts": len(part["scripts"]),
                    "background": part["background"], "events": sorted(part.get("groups", {})), "remote": part.get("remote", False),
                    "description_bytes": part.get("description_bytes", 0), "replaced": bool(part["replace"]),
                    "files": files_record, "entries": entries}
            for relative in docs:
                if docs[relative] != _json_doc(originals[relative], relative):
                    undo.append((relative, originals[relative], None))
                    _write(target, relative, _json_bytes(docs[relative], originals[relative]))
            for package in plan["packages"]:
                if package["name"] in record["packages"] and package["name"] in plan.get("retired_by", {}):
                    record["packages"][package["name"]]["retired_oaw_skills"] = plan["retired_by"][package["name"]]
            previous_record = _read(target, RECORD_PATH)
            undo.append((RECORD_PATH, previous_record, None))
            _write(target, RECORD_PATH, record_bytes(record))
        except (OSError, InstallError, ValueError) as exc:
            problems = []
            for relative, data, mode in reversed(undo):
                try:
                    if data is None:
                        _delete(target, relative)
                    else:
                        _write(target, relative, data, mode)
                except (OSError, InstallError) as error:
                    problems.append(str(error))
            raise InstallError(f"Install failed and was rolled back: {exc}" + ("; rollback issues: " + "; ".join(problems) if problems else "")) from exc
    return record


def _package_record(package: dict, plan: dict, stamp: str) -> dict:
    source = package["source"]
    return {"name": package["name"], "added_at": stamp, "choice": plan["choice"], "category": package["category"],
            "source": {"kind": source["kind"], "display": source["display"], "key": source["key"], "url": source["url"],
                       "path": source["path"], "ref": source["ref"], "commit": source.get("commit"),
                       "tree_sha256": source["tree_sha256"], "from_verdicts": source.get("from_verdicts")},
            "license": {"spdx": package["license"]["spdx"], "distribution": package["license"]["distribution"]},
            "tasting_at_install": {k: package["tasting"].get(k) for k in ("status", "label_zh", "date", "from")},
            "recommendation": package["recommendation"],
            "consents": sorted(plan["consents"] or ()), "dependencies": package["dependencies"],
            "left_out": package["left_out"], "parts": {}}


def apply_add(plan_args: dict, *, plan: dict | None = None) -> dict:
    """Apply a planned `add`: OAW's side of the choice first, then the user's parts, then the receipt."""
    plan = plan or plan_add(**plan_args)
    if plan["open_conflicts"] or plan["consent_needed"]:
        raise NeedsChoice(plan)
    step = plan["oaw_step"]
    if step["blocked"]:
        raise InstallError(step["blocked"])
    retired_by = {}
    for conflict in plan["conflicts"]:
        if conflict["type"] == "overlap" and conflict["decision"] == "use-theirs":
            retired_by.setdefault(conflict["subject"], []).extend(conflict["with"])
    for package in plan["packages"]:
        if package["name"] in retired_by and not any(p["status"] == "install" for p in package["parts"]):
            raise InstallError(f"{package['name']}: use-theirs retires OAW's {', '.join(retired_by[package['name']])}, "
                               "but none of its parts would be installed; nothing was changed.")
    oaw_result = run_oaw_step(step)
    # Plan again against the project as the OAW step left it, with the same answers and fetched bytes.
    again = plan_add(**{**plan_args, "choice": plan["choice"], "consent": plan["consents"], "snapshots": plan["snapshots"],
                        "verdicts": plan["verdicts"], "retire_hint": set(plan["retire"])})
    if again["oaw_step"]["kind"] != "none" or again["open_conflicts"] or again["consent_needed"]:
        raise InstallError("The project changed while OAW's side was applied; run the command again.")
    again["retired_by"] = retired_by
    record = commit_parts(again["target"], again) if any(p["status"] == "install" for pk in again["packages"] for p in pk["parts"]) else again["record"]
    setting = oaw.remember_checkout()
    rows = receipt_rows(again["target"], oaw.read_manifest(again["target"]), record, again["verdicts"])
    return {"status": "installed", "target": str(again["target"]), "choice": again["choice"], "oaw_step": _step_view(step, oaw_result),
            "packages": [_package_view(p) for p in again["packages"]], "notes": again["notes"], "receipt": rows,
            "checkout_setting": setting}


class NeedsChoice(InstallError):
    def __init__(self, plan: dict):
        super().__init__("A choice is needed: " + "; ".join(
            [c["text"] + " → " + "/".join(c["options"]) for c in plan["open_conflicts"]]
            + [f"consent for {need}: {', '.join(p['name'] for p in parts)}" for need, parts in plan["consent_needed"].items()]))
        self.plan = plan


# --------------------------------------------------------------------------- views: preview, question, receipt

def _step_view(step: dict, result: dict | None = None) -> dict:
    view = {"kind": step["kind"], "skills": step["skills"], "blocked": step["blocked"],
            "actions": [{"path": a["path"], "action": a["action"]} for a in step["actions"]]}
    if result and result.get("backup"):
        view["backup"] = result["backup"]
    return view


def _package_view(package: dict) -> dict:
    source = package["source"]
    return {"name": package["name"], "source": {k: source.get(k) for k in ("kind", "display", "url", "ref", "commit", "tree_sha256", "from_verdicts")},
            "status": package["status"], "reason": package["reason"], "tasting": package["tasting"], "category": package["category"],
            "recommendation": package["recommendation"], "license": package["license"]["spdx"],
            "license_distribution": package["license"]["distribution"], "dependencies": package["dependencies"],
            "static_flags": package["flags"], "left_out": package["left_out"],
            "parts": [{"name": p["name"], "kind": p["kind"], "status": p["status"], "reason": p["reason"], "needs": p["needs"],
                       "renamed_from": p["renamed_from"], "explicit_only": p["explicit_only"], "replace": bool(p["replace"]),
                       "files": sorted(p.get("writes", {})), "shared_entries": _shared_entries(p),
                       "scripts": p["scripts"], "background": p["background"]} for p in package["parts"]]}


def question_text(plan: dict) -> str:
    """The one question `add` asks: the choice, every open conflict and consent for what runs on its own."""
    names = "、".join(p["name"] for p in plan["packages"]) or "（沒有新的來源）"
    state = plan["state"]
    lines = [f"要加：{names}。回答一題就開始裝：", "", "選擇（1、2 或 3；直接按 Enter = " + {"oaw": "1", "only": "2", "recommended": "3"}[plan["default_choice"]] + "）"]
    only_note = ""
    if state == "oaw":
        only_note = "（這個專案已裝 OAW：會移除 OAW 的 skill 和輔助檔，你改過的檔案留著）"
    lines += [f"  1 ① OAW + 你加的 skill{'（預設）' if plan['default_choice'] == 'oaw' else ''}：保留 OAW 的審查、地圖、證據，把它們加進來"
              + ("（這個專案還沒裝 OAW：會一起裝）" if state != "oaw" else ""),
              f"  2 ② 只用你加的 skill{'（預設）' if plan['default_choice'] == 'only' else ''}：不裝 OAW 的 skill 和政策文字，OAW 只管清單、移除、還原" + only_note,
              "  3 ③ 建議組合：照 OAW 的試吃紀錄決定裝哪些、哪些只在你叫它時用、哪些不建議（各附一句理由）"]
    if plan["conflicts"]:
        lines.append("衝突（不寫就用第一個做法）")
        for conflict in plan["conflicts"]:
            lines.append(f"  {conflict['subject']}：{conflict['text']} → {' / '.join(conflict['options'])}")
    if plan["consent_needed"] or plan["consents"] is None and any(p["needs"] for pk in plan["packages"] for p in pk["parts"]
                                                                  if p["status"] in ("install", "needs-consent")):
        lines.append("會自己執行、要你同意才裝（不寫 = 不同意，這些不裝）")
        for need in CONSENTS:
            parts = [p for pk in plan["packages"] for p in pk["parts"] if need in p["needs"] and p["status"] in ("needs-consent", "install")]
            if parts:
                detail = "、".join(_runs_text(p) for p in parts)
                lines.append(f"  {need}：{detail}")
    needs = [n for n in CONSENTS if any(n in p["needs"] for pk in plan["packages"] for p in pk["parts"]
                                        if p["status"] in ("install", "needs-consent", "needs-decision"))]
    example = " ".join(["1", *([",".join(needs)] if needs else []),
                        *([f"{plan['conflicts'][0]['subject']}={plan['conflicts'][0]['options'][0]}"] if plan["conflicts"] else [])])
    lines += [f"回答格式：選擇 [同意的種類] [名字=做法 ...]，例如：{example}；0 = 取消"]
    return "\n".join(lines)


def suggested_command(plan: dict, sources) -> str:
    parts = ["python3", "<OAW>/scripts/oaw.py", "add", *sources, "--target", ".", "--choice", plan["choice"]]
    needs = sorted({n for pk in plan["packages"] for p in pk["parts"] for n in p["needs"]
                    if p["status"] in ("install", "needs-consent", "needs-decision")})
    if needs:
        parts += ["--consent", ",".join(needs) if plan["consents"] is None else (",".join(sorted(plan["consents"])) or "none")]
    for conflict in plan["conflicts"]:
        parts += ["--on-conflict", f"{conflict['subject']}={conflict['decision'] or conflict['options'][0]}"]
    return " ".join(parts + ["--apply"])


def _runs_text(part: dict) -> str:
    if part["kind"] == "hooks":
        return f"{part['name']}（hook：{'、'.join(part.get('events') or sorted(part.get('groups', {})))}）"
    if part["kind"] == "mcp":
        return f"{part['name']}（MCP server{'，遠端' if part.get('remote') else ''}）"
    count = part["scripts"] if isinstance(part["scripts"], int) else len(part["scripts"])
    return f"{part['name']}（{count} 個 script）"


def preview_lines(plan: dict, sources) -> list:
    lines = [f"OAW add preview: {plan['target']}（現在：{ {'clean': '還沒裝 OAW', 'oaw': '已裝 OAW', 'only': '只當管理員'}[plan['state']] }；選擇 {CHOICE_ZH[plan['choice']]}）"]
    step = plan["oaw_step"]
    if step["kind"] != "none":
        label = {"init": "安裝 OAW", "manager-only": "改成只當管理員（OAW 的 skill 和輔助檔移除，改過的留著）",
                 "retire": "移除你選擇不用的 OAW skill", "hosts": "OAW 補上新主機的 skill 資料夾"}[step["kind"]]
        lines.append(f"  OAW：{label}，{len(step['actions'])} 個檔案變動" + (f"；擋住：{step['blocked']}" if step["blocked"] else ""))
        # A first install only adds; list what retires, is kept as yours, or conflicts.
        shown = [a for a in step["actions"] if a["action"] != "add"]
        for action in shown[:12]:
            lines.append(f"    {action['action']:22} {action['path']}")
        if len(shown) > 12:
            lines.append(f"    …還有 {len(shown) - 12} 個")
    for package in plan["packages"]:
        source = package["source"]
        pin = (source.get("commit") or "")[:7] or "tree " + source["tree_sha256"][:8]
        lines.append(f"  {package['name']}：{source['display']}@{pin} · 授權 {package['license']['spdx'] or '不明'} · {tasting_text(package['tasting'], package['name'])}")
        if package["recommendation"]:
            lines.append(f"    ③ {package['recommendation']['reason']}")
        if package["status"] != "install" and package["reason"] != (package["recommendation"] or {}).get("reason"):
            lines.append(f"    不裝：{package['reason']}")
        for part in package["parts"]:
            if package["status"] != "install":
                break
            renamed = f"（原名 {part['renamed_from']}）" if part["renamed_from"] else ""
            mark = {"install": "裝", "skip": "不裝", "needs-consent": "待同意", "needs-decision": "待決定", "blocked": "擋住"}[part["status"]]
            detail = f"{len(part.get('writes', {}))} 個檔案" + (f"，{len(_shared_entries(part))} 項共用設定" if _shared_entries(part) else "")
            lines.append(f"    [{mark}] {part['kind']} {part['name']}{renamed}：{detail}" + (f" · {part['reason']}" if part["reason"] else "")
                         + ("（只在你叫它時用）" if part["explicit_only"] else ""))
        if package["dependencies"]:
            lines.append(f"    執行期相依（OAW 不替你裝）：{', '.join(package['dependencies'][:8])}")
        if package["left_out"]:
            lines.append("    不裝的部分：" + "；".join(f"{item['part']}（{item['reason']}）" for item in package["left_out"][:4])
                         + (f"…還有 {len(package['left_out']) - 4} 個" if len(package["left_out"]) > 4 else ""))
    for note in plan["notes"]:
        lines.append(f"  注意：{note}")
    return lines


def _skill_startup(path: Path) -> str:
    try:
        fields, _body = core.parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return "未知"
    if str(fields.get("disable-model-invocation", "")).casefold() == "true":
        return "0（只在你叫它時載入）"
    return f"約 {tokens(len((fields.get('name', '') + fields.get('description', '')).encode('utf-8')))} token（描述，估計）"


def receipt_rows(target: Path, manifest: dict | None, record: dict, verdicts: dict) -> list:
    """The receipt: built-in OAW skills and every part the user added, from records only."""
    rows = []
    if manifest and manifest["profile"] != oaw.MANAGER_ONLY:
        selected = manifest.get("skills", oaw.default_skills(manifest["profile"], manifest["with_improve"]))
        for name in selected:
            host = next((h for h in manifest.get("hosts", ["codex"]) if oaw.joined(target, SKILL_ROOTS[h] + name + "/SKILL.md").is_file()), None)
            startup = _skill_startup(oaw.joined(target, SKILL_ROOTS[host] + name + "/SKILL.md")) if host else "沒裝上（oaw.py doctor）"
            origin = f"EGM 0.1.0@{oaw.EGM_COMMIT[:7]}" if name in oaw.EGM_SKILLS else f"OAW {manifest['framework_version']}"
            rows.append({"skill": name, "kind": "skill", "source": origin, "added_by": "OAW 內建", "tasting": "內建，沒有試吃紀錄",
                         "startup": startup, "runs": "無", "remove": f"oaw.py remove {name} --apply"})
    for package, entry in sorted(record["packages"].items()):
        source = entry["source"]
        pin = (source.get("commit") or "")[:7]
        origin = (f"{source['url'].removeprefix('https://')}@{pin}" if source["kind"] == "github"
                  else f"{source['display']}（內容 {source['tree_sha256'][:8]}）")
        tasting = tasting_status(target, {"key": source["key"], "commit": source.get("commit")}, verdicts)
        for name, part in sorted(entry["parts"].items()):
            if part["kind"] == "skill":
                skill_file = next((f["path"] for f in part["files"] if f["path"].endswith("/SKILL.md") and f.get("sha256")), None)
                startup = _skill_startup(oaw.joined(target, skill_file)) if skill_file else "未知"
            elif part["kind"] in ("agent", "command"):
                startup = f"約 {tokens(part['description_bytes'])} token（描述，估計）" if part["description_bytes"] else "0"
            elif part["kind"] == "hooks":
                context = [e for e in part["events"] if e.casefold() in CONTEXT_EVENTS]
                startup = (f"每次 {'、'.join(context)} 會加內容（未量測）" if context else "0（不進 context）")
            else:
                startup = "工具清單（未量測，server 沒有跑過）"
            runs = []
            if part["kind"] == "hooks":
                runs.append("hook：" + "、".join(part["events"]))
            if part["kind"] == "mcp":
                runs.append("MCP server" + ("（遠端）" if part.get("remote") else ""))
            if part["scripts"]:
                runs.append(f"{part['scripts']} 個 script")
            if part.get("background"):
                runs.append("背景程式")
            label = name if part["kind"] == "skill" else f"{name}（{ {'agent': 'agent', 'command': '指令', 'hooks': 'hook', 'mcp': 'MCP'}[part['kind']] }）"
            if part.get("renamed_from"):
                label += f"，原名 {part['renamed_from']}"
            if part.get("explicit_only"):
                label += "，只在你叫它時用"
            rows.append({"skill": label, "kind": part["kind"], "package": package, "source": origin, "added_by": "你",
                         "tasting": tasting_text(tasting, package), "startup": startup, "runs": "、".join(runs) or "無",
                         "remove": f"oaw.py remove {name}"})
    return rows


RECEIPT_HEADERS = (("skill", "skill"), ("source", "來源"), ("added_by", "誰加的"), ("tasting", "試吃結果"),
                   ("startup", "開頭多花"), ("runs", "會自己執行的東西"), ("remove", "怎麼移除"))


def receipt_lines(rows: list) -> list:
    if not rows:
        return ["吸收清單是空的：還沒有 OAW 內建或你加的 skill。"]
    lines = ["| " + " | ".join(label for _key, label in RECEIPT_HEADERS) + " |",
             "|" + "|".join("---" for _ in RECEIPT_HEADERS) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row[key]).replace("|", "/") for key, _label in RECEIPT_HEADERS) + " |")
    if any(row["tasting"].startswith("未試吃") for row in rows):
        lines.append("未試吃：先 `python3 <OAW>/scripts/catalog.py add <來源> --no-taste --target .` 登記，再 `catalog.py taste <名字>`（免費的靜態檢查），"
                     f"然後照 docs/SKILL_INTAKE.md 的附錄 A 跑試吃並 record-tasting（{TASTE_COST_ZH}）；結果會出現在這張清單。")
    return lines


# --------------------------------------------------------------------------- list, remove, doctor

def list_receipt(target) -> dict:
    target = oaw.target_path(target)
    manifest = oaw.read_manifest(target)
    record = load_record(target)
    rows = receipt_rows(target, manifest, record, load_verdicts())
    retired = sorted({s for e in record["packages"].values() for s in e.get("retired_oaw_skills", [])})
    lines = [f"OAW 吸收清單：{target}（{ {'clean': '還沒裝 OAW', 'oaw': '已裝 OAW', 'only': 'OAW 只當管理員'}[project_state(manifest)] }）",
             *receipt_lines(rows)]
    if retired:
        lines.append("你選擇用別人的版本，所以沒裝 OAW 的：" + "、".join(retired) + "（移除那份 skill 時會裝回來）")
    return {"status": "list", "target": str(target), "profile": manifest["profile"] if manifest else None, "receipt": rows,
            "retired_oaw_skills": retired, "lines": lines}


def _matches(record: dict, name: str) -> list:
    """(package, part names) that `remove NAME` means: a whole package, or the parts with that name."""
    if name in record["packages"]:
        return [(name, sorted(record["packages"][name]["parts"]))]
    found = [(package, [part]) for package, entry in record["packages"].items() for part in entry["parts"] if part == name]
    if len({package for package, _parts in found}) > 1:
        raise InstallError(f"{name} names parts of several additions ({', '.join(p for p, _ in found)}); remove one of those instead.")
    return found


def _locate(doc: dict, entry: dict):
    """Where a recorded entry still sits unchanged: (container, key or index) or None."""
    *parents, key = entry["pointer"]
    node = _get(doc, parents) if parents else doc
    if not isinstance(node, dict):
        return None
    if entry["op"] == "append":
        container = node.get(key)
        if isinstance(container, list):
            for index, value in enumerate(container):
                if value == entry["value"]:
                    return container, index
        return None
    return (node, key) if key in node and node[key] == entry["value"] else None


def _prune(doc: dict, pointer: list, baseline: dict) -> None:
    """Drop containers an entry left empty, unless the user's original file already had them."""
    for depth in range(len(pointer), 0, -1):
        path = pointer[:depth]
        node = _get(doc, path)
        if node is None:
            continue
        if node in ({}, []) and _get(baseline, path) is None:
            parent = _get(doc, path[:-1]) if depth > 1 else doc
            parent.pop(path[-1], None)
        else:
            break


def plan_remove(target: Path, record: dict, name: str) -> dict:
    """What `remove NAME` restores: file by file and entry by entry, with conflicts where the user changed things."""
    matches = _matches(record, name)
    if not matches:
        raise InstallError(f"{core.sanitize_text(name, 80)!r} is not something you added; `oaw.py list` shows what is here.")
    files, entries, conflicts = [], [], []
    removing = {(package, part) for package, parts in matches for part in parts}
    for package, parts in matches:
        for part_name in parts:
            part = record["packages"][package]["parts"][part_name]
            for item in part["files"]:
                current = _read(target, item["path"])
                current_sha = sha(current) if current is not None else None
                backup = _read(target, item["backup"]) if item.get("backup") else None
                if item.get("backup") and (backup is None or sha(backup) != item["previous_sha256"]):
                    conflicts.append({"path": item["path"], "reason": "備份不見或被改過，原本的內容沒辦法還原", "backup": item.get("backup")})
                    continue
                if current_sha == item["sha256"] or (current is None and item["sha256"] is not None):
                    action = "restore" if item["previous_sha256"] else ("delete" if current is not None else "gone")
                elif item["sha256"] is None and current is None:
                    action = "restore"
                else:
                    conflicts.append({"path": item["path"], "backup": item.get("backup"),
                                      "reason": "你在安裝之後改過這個檔案，所以留著" + (f"（原本的內容在 {item['backup']}）" if item.get("backup") else "")})
                    continue
                files.append({**item, "action": action, "package": package, "part": part_name})
            for entry in part.get("entries", []):
                entries.append({**entry, "package": package, "part": part_name})
    retire_back = []
    for package, parts in matches:
        if set(parts) == set(record["packages"][package]["parts"]):
            for skill in record["packages"][package].get("retired_oaw_skills", []):
                still = any(skill in e.get("retired_oaw_skills", []) for p, e in record["packages"].items() if p != package)
                if not still:
                    retire_back.append(skill)
    return {"matches": matches, "removing": removing, "files": files, "entries": entries, "conflicts": conflicts,
            "restore_oaw": sorted(set(retire_back))}


def remove(target, name: str, *, dry_run: bool = False, apply_builtin: bool = False) -> dict:
    target = oaw.target_path(target)
    manifest = oaw.read_manifest(target)
    record = load_record(target)
    if not _matches(record, name) and (name == "egm" or name in oaw.BUNDLED_SKILLS):
        return remove_builtin(target, manifest, name, apply=apply_builtin and not dry_run)
    plan = plan_remove(target, record, name)
    lines = [f"remove {name}: " + "、".join(f"{p}（{'、'.join(parts)}）" for p, parts in plan["matches"])]
    for item in plan["files"]:
        lines.append(f"  {({'restore': '還原', 'delete': '刪除', 'gone': '已不在'})[item['action']]:4} {item['path']}")
    for entry in plan["entries"]:
        lines.append(f"  移除設定 {entry['file']} {'.'.join(entry['pointer'])}")
    for conflict in plan["conflicts"]:
        lines.append(f"  留著 {conflict['path']}：{conflict['reason']}")
    if plan["restore_oaw"]:
        lines.append(f"  OAW 的 {'、'.join(plan['restore_oaw'])} 會裝回來")
    if dry_run:
        return {"status": "dry-run", "target": str(target), "remove": name, "files": plan["files"], "entries": plan["entries"],
                "conflicts": plan["conflicts"], "restore_oaw": plan["restore_oaw"], "lines": lines + ["預覽：沒有改任何檔案"]}
    entry_conflicts = []
    with oaw.install_lock(target):
        if record_bytes(load_record(target)) != record_bytes(record):
            raise InstallError(f"{RECORD_PATH} changed during the command; run it again.")
        for item in plan["files"]:
            if item["action"] == "restore":
                backup = _dest(target, item["backup"])
                _write(target, item["path"], backup.read_bytes(), stat.S_IMODE(backup.stat().st_mode))
            elif item["action"] == "delete":
                _delete(target, item["path"])
        for relative in SHARED_FILES:
            mine = [e for e in plan["entries"] if e["file"] == relative]
            if not mine:
                continue
            current = _read(target, relative)
            try:
                doc = _json_doc(current, relative)
            except InstallError as exc:
                entry_conflicts.extend({"path": relative, "reason": str(exc)} for _e in mine)
                continue
            shared = record["shared"].get(relative, {})
            baseline_bytes = _read(target, shared["backup"]) if shared.get("backup") else None
            baseline = _json_doc(baseline_bytes, relative) if baseline_bytes is not None else {}
            for entry in mine:
                spot = _locate(doc, entry)
                if spot is None:
                    entry_conflicts.append({"path": f"{relative} {'.'.join(entry['pointer'])}", "reason": "你改過或移除了這一項，所以沒有動"})
                    continue
                container, key = spot
                if entry["op"] == "append":
                    container.pop(key)
                elif entry.get("had_previous"):
                    container[key] = copy.deepcopy(entry["previous"])
                else:
                    container.pop(key)
                _prune(doc, entry["pointer"], baseline)
            others = any(e["file"] == relative for p, pe in record["packages"].items() for n, part in pe["parts"].items()
                         if (p, n) not in plan["removing"] for e in part.get("entries", []))
            if not others and doc == baseline:
                if baseline_bytes is not None:
                    _write(target, relative, baseline_bytes)
                else:
                    _delete(target, relative)
            elif doc != _json_doc(current, relative):
                _write(target, relative, _json_bytes(doc, current))
        conflict_paths = {c["path"] for c in plan["conflicts"]}
        for package, parts in plan["matches"]:
            entry = record["packages"][package]
            for part_name in parts:
                part = entry["parts"].pop(part_name)
                for item in part["files"]:
                    if item.get("backup") and item["path"] not in conflict_paths:
                        _delete(target, item["backup"])
            if not entry["parts"]:
                del record["packages"][package]
        for relative in list(record["shared"]):
            if not any(e["file"] == relative for pe in record["packages"].values() for part in pe["parts"].values() for e in part.get("entries", [])):
                if record["shared"][relative].get("backup"):
                    _delete(target, record["shared"][relative]["backup"])
                del record["shared"][relative]
        if record["packages"]:
            _write(target, RECORD_PATH, record_bytes(record))
        else:
            _delete(target, RECORD_PATH)
    restored = None
    if plan["restore_oaw"] and manifest and manifest["profile"] != oaw.MANAGER_ONLY:
        try:
            restored = restore_builtin(target, plan["restore_oaw"])
            lines.append(f"  OAW 的 {'、'.join(plan['restore_oaw'])} 已裝回來")
        except InstallError as exc:
            lines.append(f"  OAW 的 {'、'.join(plan['restore_oaw'])} 沒有裝回來：{exc}；用 oaw.py migrate --skills default 預覽後 --apply")
    conflicts = plan["conflicts"] + entry_conflicts
    lines.append("完成" + (f"；{len(conflicts)} 個地方你改過，留著沒動" if conflicts else "：回到加之前的樣子"))
    return {"status": "removed", "target": str(target), "remove": name, "files": plan["files"], "entries": plan["entries"],
            "conflicts": conflicts, "restored_oaw": plan["restore_oaw"] if restored else [], "lines": lines}


def _builtin_change(target: Path, manifest: dict, names: list, *, adding: bool) -> dict:
    selected = list(manifest.get("skills", oaw.default_skills(manifest["profile"], manifest["with_improve"])))
    selection = sorted(set(selected) | set(names)) if adding else [s for s in selected if s not in names]
    plan = oaw.plan_install(target, manifest["profile"], manifest["with_improve"], migrate=True,
                            hosts=manifest.get("hosts", ["codex"]), skills=selection)
    actions = [a for a in plan["actions"] if a["action"] not in ("unchanged", "preserve")]
    if not adding and any(a["action"] == "add" for a in actions):
        raise InstallError("This removal would also install other files; resolve the recipe with `oaw.py migrate` first.")
    if adding and any(a["action"].startswith("retire") for a in actions):
        raise InstallError("This re-add would also retire other files; resolve the recipe with `oaw.py migrate` first.")
    return {"plan": plan, "actions": actions, "selected": selected, "selection": selection}


def restore_builtin(target: Path, names: list) -> dict:
    manifest = oaw.read_manifest(target)
    change = _builtin_change(target, manifest, names, adding=True)
    return oaw.apply_plan(change["plan"], migrate=True)


def remove_builtin(target: Path, manifest: dict | None, name: str, *, apply: bool) -> dict:
    """A built-in OAW skill leaves through migrate's recipe change: preview, then --apply (backed up)."""
    if not manifest or manifest["profile"] == oaw.MANAGER_ONLY:
        raise InstallError(f"{name} is not installed here.")
    names = list(oaw.EGM_SKILLS) if name == "egm" else [name]
    change = _builtin_change(target, manifest, names, adding=False)
    if not set(names) & set(change["selected"]):
        raise InstallError(f"{name} is not in this project's OAW recipe.")
    lines = [f"remove {name} (built-in OAW skill) through oaw.py migrate; recipe after: {', '.join(change['selection']) or 'no bundled skills'}"]
    lines += [f"  {a['action']:22} {a['path']}" for a in change["actions"]]
    conflicts = [a["path"] for a in change["actions"] if a["action"] in ("conflict", "retire-conflict")]
    if not apply:
        lines.append(f"預覽：加 --apply 才移除（會先備份）；裝回來用 oaw.py migrate --skills default --apply")
        return {"status": "preview", "target": str(target), "remove": name, "actions": change["actions"], "conflicts": conflicts, "lines": lines}
    if conflicts:
        raise InstallError("Edited files block this removal; resolve them with `oaw.py migrate` first: " + ", ".join(conflicts))
    result = oaw.apply_plan(change["plan"], migrate=True)
    lines.append(f"完成；備份在 {result['backup']}")
    return {"status": "removed", "target": str(target), "remove": name, "actions": change["actions"], "backup": result["backup"], "lines": lines}


def doctor_checks(target: Path) -> list:
    """Doctor rows for the user's own additions: files still as installed, settings entries still there."""
    checks = []
    try:
        record = load_record(target)
    except (InstallError, OSError, ValueError) as exc:
        return [{"status": "FAIL", "path": RECORD_PATH, "detail": str(exc)}]
    docs = {}
    for relative in SHARED_FILES:
        try:
            docs[relative] = _json_doc(_read(target, relative), relative)
        except (InstallError, OSError) as exc:
            docs[relative] = None
            checks.append({"status": "WARN", "path": relative, "detail": str(exc)})
    for package, entry in sorted(record["packages"].items()):
        for name, part in sorted(entry["parts"].items()):
            for item in part["files"]:
                if not item.get("sha256"):
                    continue
                try:
                    current = _read(target, item["path"])
                except (InstallError, OSError) as exc:
                    checks.append({"status": "FAIL", "path": item["path"], "detail": str(exc)})
                    continue
                if current is None:
                    checks.append({"status": "FAIL", "path": item["path"], "detail": f"Added by you ({package}/{name}) and now missing; `oaw.py remove {name}` restores the earlier state."})
                elif sha(current) != item["sha256"]:
                    checks.append({"status": "WARN", "path": item["path"], "detail": f"Added by you ({package}/{name}) and edited since; remove keeps your edit."})
                else:
                    checks.append({"status": "PASS", "path": item["path"], "detail": f"Added by you ({package}/{name}); unchanged."})
            for item in part.get("entries", []):
                doc = docs.get(item["file"])
                if doc is not None and _locate(doc, item) is None:
                    checks.append({"status": "WARN", "path": item["file"], "detail": f"The {'.'.join(item['pointer'])} entry of {package}/{name} was changed or removed."})
    return checks


# --------------------------------------------------------------------------- command line

def _interactive(args) -> bool:
    return not args.json and args.choice is None and sys.stdin.isatty() and sys.stdout.isatty()


def parse_answer(text: str, plan: dict) -> dict | None:
    """One answer to the question: choice, consents and NAME=ACTION decisions. None cancels."""
    answer = {"choice": plan["default_choice"], "consent": set(), "decisions": {}}
    for token in str(text or "").replace("，", " ").replace("、", ",").split():
        lowered = token.casefold()
        if lowered in ("0", "q", "cancel", "取消"):
            return None
        if lowered in CHOICE_ALIASES or lowered in CHOICES:
            answer["choice"] = CHOICE_ALIASES.get(lowered, lowered)
        elif "=" in token:
            answer["decisions"].update({k: {**answer["decisions"].get(k, {}), **v} for k, v in _decisions([token]).items()})
        else:
            answer["consent"] |= _consents(lowered)
    return answer


def add(target, sources, *, choice=None, consent=None, on_conflict=(), host=None, apply=False, ask=None, verdicts=None) -> tuple:
    """`oaw.py add`: (result, exit code). `ask(question) -> answer` makes it interactive (one question)."""
    plan_args = {"target": target, "sources": list(sources), "choice": choice, "consent": consent,
                 "on_conflict": on_conflict, "host": host, "verdicts": verdicts}
    plan = plan_add(**plan_args)
    if ask is not None:
        prompt = "\n".join(preview_lines(plan, sources)) + "\n\n" + question_text(plan) + "\n> "
        for _attempt in range(3):
            try:
                answer = parse_answer(ask(prompt), plan)
                break
            except InstallError as exc:
                prompt = f"看不懂：{exc}\n> "
        else:
            answer = None
        if answer is None:
            return {"status": "cancelled", "target": str(plan["target"]), "lines": ["取消：沒有改任何檔案"]}, 0
        decisions = _decisions(on_conflict)
        for name, value in answer["decisions"].items():
            decisions.setdefault(name, {}).update(value)
        plan_args.update(choice=answer["choice"], consent=answer["consent"] | (_consents(consent) or set()),
                         on_conflict=decisions, interactive_defaults=True, verdicts=plan["verdicts"], snapshots=plan["snapshots"])
        plan = plan_add(**plan_args)
        apply = True
    if not apply:
        result = {"status": "preview", "target": str(plan["target"]), "state": plan["state"], "choice": plan["choice"],
                  "default_choice": plan["default_choice"], "hosts": plan["hosts"], "oaw_step": _step_view(plan["oaw_step"]),
                  "packages": [_package_view(p) for p in plan["packages"]], "conflicts": plan["conflicts"],
                  "consent_needed": {k: [p["name"] for p in v] for k, v in plan["consent_needed"].items()},
                  "notes": plan["notes"], "question": question_text(plan), "apply_command": suggested_command(plan, sources)}
        result["lines"] = preview_lines(plan, sources) + ["", "預覽：沒有寫任何檔案。要裝請回答下面這一題（或直接用最後一行的指令）：",
                                                          question_text(plan), "", result["apply_command"]]
        return result, 0
    plan_args.update(verdicts=plan["verdicts"], snapshots=plan["snapshots"], consent=plan["consents"], choice=plan["choice"],
                     on_conflict=plan_args["on_conflict"])
    try:
        result = apply_add(plan_args, plan=plan)
    except NeedsChoice as exc:
        result = {"status": "needs-choice", "target": str(plan["target"]), "error": str(exc), "question": question_text(exc.plan),
                  "conflicts": exc.plan["open_conflicts"], "consent_needed": {k: [p["name"] for p in v] for k, v in exc.plan["consent_needed"].items()},
                  "apply_command": suggested_command(exc.plan, sources)}
        result["lines"] = [str(exc), question_text(exc.plan), "", result["apply_command"]]
        return result, EXIT_CHOICE
    result["lines"] = [f"OAW add：完成（{CHOICE_ZH[result['choice']]}）"]
    if result["oaw_step"]["kind"] != "none":
        result["lines"].append(f"  OAW：{result['oaw_step']['kind']}，{len(result['oaw_step']['actions'])} 個檔案變動"
                               + (f"，備份在 {result['oaw_step']['backup']}" if result["oaw_step"].get("backup") else ""))
    for package in result["packages"]:
        installed = [p["name"] for p in package["parts"] if p["status"] == "install"]
        skipped = [f"{p['name']}（{p['reason']}）" for p in package["parts"] if p["status"] != "install"]
        result["lines"].append(f"  {package['name']}：裝了 {'、'.join(installed) or '無'}" + (f"；沒裝 {'；'.join(skipped)}" if skipped else "")
                               + (f"；{package['reason']}" if package["status"] != "install" and not package["parts"] else ""))
    result["lines"] += [f"  注意：{note}" for note in result["notes"]]
    result["lines"] += ["", *receipt_lines(result["receipt"])]
    return result, 0


def _print(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps({k: v for k, v in result.items() if k != "lines"}, indent=2, ensure_ascii=False, default=str))
    else:
        print("\n".join(result.get("lines", [])))


def run(args) -> int:
    """Entry from oaw.py for add, list and remove."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    try:
        if sys.version_info < (3, 10):
            raise InstallError("Python 3.10+ is required.")
        if args.command == "add":
            if not args.sources and args.choice is None:
                raise InstallError("Name at least one SOURCE, or a --choice to apply on its own.")
            ask = (lambda prompt: input(prompt)) if _interactive(args) else None
            result, code = add(args.target, args.sources, choice=args.choice, consent=args.consent, on_conflict=args.on_conflict,
                               host=args.host, apply=args.apply, ask=ask)
        elif args.command == "list":
            result, code = list_receipt(args.target), 0
        else:
            result = remove(args.target, args.name, dry_run=args.dry_run, apply_builtin=args.apply)
            code = 0
    except (InstallError, OSError, UnicodeError, core.SourceError, ValueError) as exc:
        result, code = {"status": "error", "error": str(exc), "lines": [f"OAW error: {exc}"]}, 2
    _print(result, args.json)
    return code
