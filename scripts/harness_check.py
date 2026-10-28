#!/usr/bin/env python3
"""One local/CI entry point for OAW's executable contracts."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import py_compile
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def configure_stdio():
    # Redirected Windows runners can otherwise use cp1252 for Unicode diagnostics.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


@dataclass
class Check:
    name: str
    passed: bool
    detail: str
    stdout: str = ""
    stderr: str = ""


def run(command, *, cwd=ROOT, env=None):
    environment = os.environ.copy()
    environment.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    if env:
        environment.update(env)
    return subprocess.run(command, cwd=cwd, env=environment, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=180)


def command_check(name, command):
    process = run(command)
    return Check(name, process.returncode == 0, f"exit {process.returncode}", process.stdout, process.stderr)


def syntax_check():
    targets = sorted((ROOT / "scripts").glob("*.py")) + sorted((ROOT / "tests").glob("test_*.py"))
    with tempfile.TemporaryDirectory(prefix="oaw-compile-") as temporary:
        for index, source in enumerate(targets):
            py_compile.compile(str(source), cfile=str(Path(temporary) / f"{index}.pyc"), doraise=True)
    return Check("syntax", True, f"{len(targets)} Python files compiled")


def cli_check():
    required = {"oaw.py": ("init", "migrate", "doctor"),
                "context_hub.py": ("memory", "search"), "wiki_sync.py": ("refresh", "lint"),
                "improvement.py": ("propose", "compare", "decide")}
    for script, commands in required.items():
        process = run([sys.executable, str(ROOT / "scripts" / script), "--help"])
        if process.returncode or any(command not in process.stdout for command in commands):
            return Check("cli-contracts", False, f"{script} help is invalid", process.stdout, process.stderr)
    return Check("cli-contracts", True, f"{len(required)} entry points expose expected operations")


def install_check():
    with tempfile.TemporaryDirectory(prefix="oaw-install-") as temporary:
        target = Path(temporary) / "project with spaces"
        commands = [
            [sys.executable, str(ROOT / "scripts/oaw.py"), "init", "--target", str(target), "--json"],
            [sys.executable, str(ROOT / "scripts/oaw.py"), "init", "--target", str(target), "--profile", "knowledge", "--with-improve", "--json"],
            [sys.executable, str(ROOT / "scripts/oaw.py"), "init", "--target", str(target), "--host", "both", "--json"],
            [sys.executable, str(ROOT / "scripts/oaw.py"), "doctor", "--target", str(target), "--json"],
            [sys.executable, str(target / "scripts/context_hub.py"), "status", "--compact"],
            [sys.executable, str(target / "scripts/wiki_sync.py"), "lint"],
            [sys.executable, str(target / "scripts/improvement.py"), "--help"],
        ]
        for command in commands:
            process = run(command)
            if process.returncode:
                return Check("installed-lifecycle", False, "fresh/additive installation or installed helper failed",
                             process.stdout, process.stderr)
        preview = run([sys.executable, str(ROOT / "scripts/oaw.py"), "migrate", "--target", str(target), "--json"])
        if preview.returncode or json.loads(preview.stdout).get("status") != "dry-run":
            return Check("installed-lifecycle", False, "migrate default must be a preview", preview.stdout, preview.stderr)
        return Check("installed-lifecycle", True, "minimal -> knowledge+improvement+both hosts; doctor and installed helpers; dry-run migration")


def version_check():
    import oaw
    version = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
    if version.get("version") != oaw.FRAMEWORK_VERSION:
        return Check("version", False, "VERSION.json differs from installer version")
    if version.get("release_status") not in ("proposed", "released"):
        return Check("version", False, "release_status must be explicit")
    return Check("version", True, f"{version['version']} ({version['release_status']})")


def main(argv=None):
    configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)
    checks = []
    operations = [
        ("syntax", syntax_check),
        ("cli-contracts", cli_check),
        ("native-skills", lambda: command_check("native-skills", [sys.executable, "scripts/validate_skills.py"])),
        ("behavior-regressions", lambda: command_check("behavior-regressions", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"])),
        ("installed-lifecycle", install_check),
        ("example-content", lambda: command_check("example-content", [sys.executable, "scripts/sync_examples.py"])),
        ("repo-wiki", lambda: command_check("repo-wiki", [sys.executable, "scripts/wiki_sync.py", "lint"])),
        ("version", version_check),
    ]
    for name, operation in operations:
        try:
            checks.append(operation())
        except Exception as exc:
            checks.append(Check(name, False, f"{type(exc).__name__}: {exc}"))
    passed = sum(check.passed for check in checks)
    report = {"all_passed": bool(checks) and passed == len(checks), "passed_count": passed,
              "total": len(checks), "checks": [asdict(check) for check in checks]}
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for check in checks:
            print(f"{'PASS' if check.passed else 'FAIL'} {check.name}: {check.detail}")
            if args.verbose or not check.passed:
                if check.stdout.strip():
                    print(check.stdout.rstrip())
                if check.stderr.strip():
                    print(check.stderr.rstrip())
        print(f"{passed}/{len(checks)} checks passed")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
