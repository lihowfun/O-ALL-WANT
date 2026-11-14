#!/usr/bin/env python3
"""Vendor the pinned complete EGM runtime and generate native OAW bridges.

Reads Git objects, never checks out or executes upstream code. Runtime file
patterns are adapted from Google's Apache-2.0 scripts/pack_plugin.py at COMMIT.
No network, global host configuration or model requests.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile
import validate_skills

# Runtime selection patterns adapted from Google's pack_plugin.py (Apache-2.0).
# Copyright 2026 Google LLC. OAW adapter/generator changes are documented in
# vendor/README.md; upstream runtime bytes and license remain unchanged.

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "f0ba151b252c9abf1318d9fe857a43265d06de89"
REPOSITORY = "https://github.com/google/elephant-goldfish-model"
SKILLS = ("egm-bootstrap", "egm-brainstorm", "egm-draft", "egm-drift-report", "egm-resolve", "egm-review", "egm-review-loop")
PATTERNS = (
    "plugin.json", "LICENSE", "README.md", "skills/*/SKILL.md",
    "skills/*/agents/openai.yaml", "skills/*/assets/*.svg", "skills/*/assets/*.png",
    "skills/*/references/*.md", "skills/*/references/*.json", "agents/*.md",
    "resources/*.md", "resources/document_standards/*.md", "docs/index.md",
    "docs/getting_started.md", "docs/harnesses.md", "docs/claude.md", "docs/codex.md",
    "docs/faq.md", "docs/privacy.md", "docs/releases.md", "assets/*.svg", "assets/*.png",
    "docs/assets/*.svg", "docs/assets/*.png", ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json", ".claude-plugin/icon.png", ".claude-plugin/agents/*.md",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def matches(name, pattern):
    return re.fullmatch(re.escape(pattern).replace(r"\*", "[^/]*"), name) is not None


def git_archive(repo):
    command = ["git", "-c", "safe.directory=" + Path(repo).resolve().as_posix(), "-c", "core.autocrlf=false", "-c", "core.eol=lf", "-C", str(repo), "archive", "--format=zip", COMMIT]
    raw = subprocess.check_output(command)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        result = {}
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Unsafe upstream archive path")
            if not info.is_dir():
                result[path.as_posix()] = archive.read(info)
        return result


def bridges(runtime):
    result = {}
    for name in SKILLS:
        fields, _ = validate_skills._frontmatter(runtime[f"skills/{name}/SKILL.md"].decode("utf-8"))
        if fields["name"] != name:
            raise ValueError("Upstream skill name mismatch")
        manual = fields.get("disable-model-invocation", False)
        front = ("---\nname: " + name + "\ndescription: " + json.dumps(fields["description"], ensure_ascii=False)
                 + "\nlicense: Apache-2.0\ndisable-model-invocation: " + str(manual).lower() + "\n---\n\n")
        body = (f"# {name}\n\nRead the complete, unmodified upstream entry before using this skill:\n\n"
                f"`../../../.oaw/integrations/egm/skills/{name}/SKILL.md`\n\n"
                "Resolve that path from this SKILL.md directory (works for both native host layouts). "
                "Resolve the upstream entry's relative references from its own directory, not this bridge. "
                "The runtime includes all personas, standards, host instructions and licenses.\n\n"
                "Project-install bindings: resolve the upstream runtime root to an absolute path. "
                "In upstream text, `${CLAUDE_PLUGIN_ROOT}` means that resolved root; the host does not "
                "substitute it in project files. Plugin-qualified `egm:egm-*` names map to the "
                "project's `egm-*` skill/agent names. Read the corresponding bundled entry when "
                "the workflow calls another manual skill. Standalone marketplace installation "
                "instructions describe an alternative installation; this project already has the "
                "complete pinned runtime. Preserve all upstream stage, tool, isolation and human "
                "checkpoint requirements. If the host cannot provide them, report the missing "
                "capability and stop that workflow.\n\n"
                "This is an OAW v2 entrypoint adapter, not a rewritten EGM workflow. "
                f"Source: {REPOSITORY}/tree/{COMMIT}; manifest 0.1.0; Apache-2.0. "
                "The installed OAW_SOURCE.json records exact upstream file hashes.\n")
        root = f"templates/.agents/skills/{name}/"
        result[root + "SKILL.md"] = (front + body).encode("utf-8")
        ui = runtime[f"skills/{name}/agents/openai.yaml"].decode("utf-8")
        if re.search(r"(?m)^policy:", ui):
            raise ValueError("Review changed upstream invocation policy before updating")
        ui += "\n# OAW adapter: preserve the upstream skill's invocation policy.\npolicy:\n  allow_implicit_invocation: " + str(not manual).lower() + "\n"
        result[root + "agents/openai.yaml"] = ui.encode("utf-8")
        prefix = f"skills/{name}/assets/"
        for path, data in runtime.items():
            if path.startswith(prefix):
                result[root + "assets/" + path.removeprefix(prefix)] = data
    for path, data in runtime.items():
        if not path.startswith(".claude-plugin/agents/") or not path.endswith(".md"):
            continue
        text = data.decode("utf-8")
        match = re.search(r"(?m)^name:\s*(egm-[a-z0-9-]+)\s*$", text)
        if not match:
            raise ValueError("Missing canonical native agent name")
        # Keep all native tools/model/omitClaudeMd restrictions unchanged.
        # Only the plugin-root binding differs in a project installation.
        text = text.replace("${CLAUDE_PLUGIN_ROOT}", ".oaw/integrations/egm").replace("egm:egm-", "egm-")
        end = text.index("\n---", 4) + len("\n---")
        note = ("\n\nOAW v2 adapter: resolve `.oaw/integrations/egm` from the project root "
                "containing `.oaw/install.json`; use the absolute runtime path supplied by the caller "
                "when available. Upstream plugin-qualified egm:egm-* names refer to project egm-* "
                "agents here. The canonical persona and native restrictions are unchanged.\n")
        text = text[:end] + note + text[end:]
        result[f"templates/.claude/agents/{match.group(1)}.md"] = text.encode("utf-8")
    return result


def build(repo):
    archive = git_archive(repo)
    runtime = {name: data for name, data in archive.items() if any(matches(name, p) for p in PATTERNS)}
    for name in ("plugin.json", "LICENSE", "README.md", "docs/codex.md", "docs/claude.md", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        if name not in runtime:
            raise ValueError("Incomplete upstream runtime: " + name)
    portable = json.loads(runtime["plugin.json"])
    if portable.get("version") != "0.1.0":
        raise ValueError("Pinned upstream manifest version changed")
    for name in ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        manifest = json.loads(runtime[name])
        if manifest.get("hooks") or any(manifest.get(k) for k in ("mcpServers", "mcp", "apps")):
            raise ValueError("Unreviewed upstream runtime dependencies")
        for reference in manifest.get("agents", []):
            relative = PurePosixPath(reference).as_posix().removeprefix("./")
            if relative not in runtime:
                raise ValueError("Unbundled host persona: " + reference)
    lock = {"schema_version": 1, "repository": REPOSITORY, "commit": COMMIT, "version": "0.1.0",
            "license": "Apache-2.0", "skills": list(SKILLS), "packaging_source": "scripts/pack_plugin.py",
            "packaging_sha256": sha(archive["scripts/pack_plugin.py"]),
            "files": {name: sha(data) for name, data in sorted(runtime.items())},
            "modifications": "Upstream runtime bytes unchanged. Native entry bridges and invocation-policy adapters are generated by scripts/sync_egm.py."}
    result = {"vendor/egm/" + name: data for name, data in runtime.items()}
    result["vendor/egm/OAW_SOURCE.json"] = (json.dumps(lock, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    result.update(bridges(runtime))
    return result


def verify_bundled():
    """Check the source pin and every generated adapter without network/Git."""
    import oaw
    payload = oaw.egm_payload()
    runtime = {name.removeprefix(oaw.EGM_RUNTIME): data for name, data in payload.items()
               if not name.endswith("/OAW_SOURCE.json")}
    expected = bridges(runtime)
    actual = {p.relative_to(ROOT).as_posix() for parent in (
        *(ROOT / "templates/.agents/skills" / name for name in SKILLS),
        ROOT / "templates/.claude/agents") for p in parent.rglob("*") if p.is_file()}
    if actual != set(expected):
        raise ValueError("EGM adapter inventory differs from the pinned generator")
    for name, data in expected.items():
        path = ROOT / name
        oaw.check_path(path, kind="file")
        if path.read_bytes() != data:
            raise ValueError("Generated EGM adapter changed: " + name)
    return {"runtime_files": len(runtime), "adapter_files": len(expected), "commit": COMMIT}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--repo", help="local EGM Git clone containing the pinned commit")
    mode.add_argument("--check-bundled", action="store_true", help="verify committed runtime and adapters offline")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.check_bundled:
        if args.write:
            parser.error("--write requires --repo")
        print(json.dumps({"status": "verified", **verify_bundled()}))
        return 0
    expected = build(args.repo)
    changed = []
    for name, data in sorted(expected.items()):
        path = ROOT / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p.is_relative_to(ROOT)):
            raise ValueError("Refusing symlink in generated destination")
        if not path.is_file() or path.read_bytes() != data:
            changed.append(name)
            if args.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
    if changed and not args.write:
        print(json.dumps({"status": "drift", "paths": changed}))
        return 1
    print(json.dumps({"status": "written" if args.write else "verified", "files": len(expected), "commit": COMMIT, "skills": list(SKILLS)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
