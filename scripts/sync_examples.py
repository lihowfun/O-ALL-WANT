#!/usr/bin/env python3
"""Generate/check the examples' framework files from the actual installer payload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import oaw

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = (("minimal-project", "minimal", False), ("public-hybrid-demo", "knowledge", True))


def manifest(profile, learning, payload, name):
    return {
        "schema_version": 1,
        "framework_version": oaw.FRAMEWORK_VERSION,
        "installation_id": "generated-example-" + name,
        "profile": profile,
        "with_improve": learning,
        "custom_files": [],
        "hosts": ["codex"],
        "managed_files": {key: oaw.digest(value) for key, value in payload.items() if not key.startswith("docs/")},
        "runtime": {"minimum_python": "3.10", "state": "project files", "host_settings": "not configured"},
        "status": "installed",
        "pending_conflicts": [],
    }


def expected_files(name, profile, learning):
    payload = oaw.source_files(profile, learning)
    result = dict(payload)
    if name == "public-hybrid-demo":
        # The demo's real source/topic content is maintained separately from package seeds.
        result = {key: value for key, value in payload.items() if not key.startswith("docs/")}
    result[".oaw/install.json"] = oaw.json_bytes(manifest(profile, learning, payload, name))
    return result


def framework_file(relative, name):
    if name == "minimal-project":
        return relative != "README.md"
    return (relative.startswith(("scripts/", ".agents/skills/", ".oaw/"))
            or relative in {"AGENTS.md", "CLAUDE.md", "AI_CONTEXT.md", "ROADMAP.md", "VERSION.json",
                            "GEMINI.md", ".cursorrules", ".windsurfrules", ".github/copilot-instructions.md"})


def sync(write=False):
    issues = []
    for name, profile, learning in EXAMPLES:
        target = ROOT / "example" / name
        if target.is_symlink() or not target.resolve().is_relative_to((ROOT / "example").resolve()):
            raise ValueError("Example target escapes the designated example directory")
        expected = expected_files(name, profile, learning)
        actual = {}
        if target.exists():
            for path in target.rglob("*"):
                relative = path.relative_to(target).as_posix()
                if "__pycache__" in path.parts or path.name.endswith(".oaw.lock"):
                    continue
                if path.is_symlink():
                    raise ValueError(f"Symlink in generated example: {path}")
                if path.is_file() and framework_file(relative, name):
                    actual[relative] = path
        for relative, content in expected.items():
            path = target / relative
            if not path.is_file() or path.read_bytes() != content:
                if write:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
                else:
                    issues.append(f"{name}/{relative}: missing or differs from installer payload")
        for relative in sorted(set(actual) - set(expected)):
            if write:
                path = actual[relative]
                if not path.resolve().is_relative_to(target.resolve()):
                    raise ValueError("Refusing to remove a file outside the generated example")
                path.unlink()
            else:
                issues.append(f"{name}/{relative}: obsolete framework file")
    return issues


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate the known example framework files")
    args = parser.parse_args(argv)
    try:
        issues = sync(write=args.write)
    except (OSError, ValueError, oaw.InstallError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for issue in issues:
        print(issue)
    if not issues:
        print("Examples regenerated." if args.write else "Example framework files match installer payloads.")
    return int(bool(issues))


if __name__ == "__main__":
    raise SystemExit(main())
