#!/usr/bin/env python3
"""
harness_check — one-command local health gate for OAW.

Runs the same checks that CI runs, so an external contributor (or a returning
maintainer) can answer "did I break anything?" before opening a PR.

Exit code:
  0 — all checks passed
  non-zero — at least one check failed; see summary at the bottom

Checks, in order:
  1. pycompile         — syntax-check the two shipped CLI tools
  2. cli-help          — wiki_sync.py --help surfaces build/refresh/lint
  3. self-install-ref  — install.sh must refuse when run from the repo root
  4. fresh-install     — install.sh into a clean tempdir succeeds and drops
                          the expected file set
  5. wiki-lint         — wiki_sync.py lint passes on a freshly installed project
  6. repo-lint         — wiki_sync.py lint passes on the OAW repo itself
  7. strict-placeholder — wiki_sync.py lint --strict correctly fails on a
                          fresh install that still has template placeholders
  8. example-drift     — example/minimal-project/scripts/*.py == scripts/*.py

Usage:
  ./scripts/harness_check.py              # run all, print summary
  ./scripts/harness_check.py --verbose    # show each check's raw output
  ./scripts/harness_check.py --json       # emit machine-readable JSON summary
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    stdout: str = ""
    stderr: str = ""


@dataclass
class Report:
    checks: list = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def record(self, name: str, passed: bool, detail: str = "", stdout: str = "", stderr: str = "") -> None:
        self.checks.append(CheckResult(name, passed, detail, stdout, stderr))


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None, input_: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        input=input_,
        capture_output=True,
        text=True,
    )


# ── Individual checks ─────────────────────────────────────────────────────────

def check_pycompile(report: Report) -> None:
    targets = [REPO_ROOT / "scripts" / "context_hub.py", REPO_ROOT / "scripts" / "wiki_sync.py"]
    for path in targets:
        proc = _run([sys.executable, "-m", "py_compile", str(path)])
        if proc.returncode != 0:
            report.record("pycompile", False, f"failed on {path.name}", proc.stdout, proc.stderr)
            return
    report.record("pycompile", True, detail=f"{len(targets)} file(s) compiled clean")


def check_cli_help(report: Report) -> None:
    proc = _run([sys.executable, str(REPO_ROOT / "scripts" / "wiki_sync.py"), "--help"])
    if proc.returncode != 0:
        report.record("cli-help", False, "wiki_sync.py --help exited non-zero", proc.stdout, proc.stderr)
        return
    expected = ("build", "refresh", "lint")
    missing = [name for name in expected if name not in proc.stdout]
    if missing:
        report.record("cli-help", False, f"missing subcommand(s): {', '.join(missing)}", proc.stdout, proc.stderr)
        return
    report.record("cli-help", True, detail=f"all expected subcommands present: {', '.join(expected)}")


def check_self_install_refusal(report: Report) -> None:
    install_sh = REPO_ROOT / "install.sh"
    if not install_sh.exists():
        report.record("self-install-ref", False, "install.sh not found")
        return
    proc = _run(["bash", str(install_sh)], cwd=REPO_ROOT)
    if proc.returncode == 0:
        report.record("self-install-ref", False, "install.sh unexpectedly succeeded from repo root", proc.stdout, proc.stderr)
        return
    if "Refusing to install" not in (proc.stdout + proc.stderr):
        report.record("self-install-ref", False, "install.sh failed but did not explain with 'Refusing to install'", proc.stdout, proc.stderr)
        return
    report.record("self-install-ref", True, detail="install.sh refused with the expected message")


def check_fresh_install(report: Report) -> None:
    install_sh = REPO_ROOT / "install.sh"
    with tempfile.TemporaryDirectory() as tmp:
        proc = _run(["bash", str(install_sh)], cwd=tmp, input_="y\n")
        if proc.returncode != 0:
            report.record("fresh-install", False, "install.sh failed in a clean tempdir", proc.stdout, proc.stderr)
            return
        required = [
            "CLAUDE.md",
            "AI_CONTEXT.md",
            "AGENTS.md",
            "GEMINI.md",
            ".cursorrules",
            ".windsurfrules",
            ".agents/memory.md",
            "docs/knowledge/index.md",
            "scripts/wiki_sync.py",
            "scripts/context_hub.py",
        ]
        missing = [p for p in required if not (Path(tmp) / p).exists()]
        if missing:
            report.record("fresh-install", False, f"missing post-install files: {', '.join(missing)}", proc.stdout, proc.stderr)
            return
        report.record("fresh-install", True, detail=f"{len(required)} expected files present")


def check_fresh_install_wiki_lint(report: Report) -> None:
    install_sh = REPO_ROOT / "install.sh"
    with tempfile.TemporaryDirectory() as tmp:
        setup = _run(["bash", str(install_sh)], cwd=tmp, input_="y\n")
        if setup.returncode != 0:
            report.record("wiki-lint", False, "install.sh failed before lint could run", setup.stdout, setup.stderr)
            return
        proc = _run([sys.executable, "scripts/wiki_sync.py", "lint"], cwd=tmp)
        if proc.returncode != 0:
            report.record("wiki-lint", False, "wiki_sync.py lint failed on fresh install", proc.stdout, proc.stderr)
            return
        report.record("wiki-lint", True, detail="fresh-install lint exit 0")


def check_repo_lint(report: Report) -> None:
    proc = _run([sys.executable, str(REPO_ROOT / "scripts" / "wiki_sync.py"), "lint"], cwd=REPO_ROOT)
    if proc.returncode != 0:
        report.record("repo-lint", False, "wiki_sync.py lint failed on the OAW repo", proc.stdout, proc.stderr)
        return
    report.record("repo-lint", True, detail="repo lint exit 0")


def check_strict_placeholder_on_fresh_install(report: Report) -> None:
    install_sh = REPO_ROOT / "install.sh"
    with tempfile.TemporaryDirectory() as tmp:
        setup = _run(["bash", str(install_sh)], cwd=tmp, input_="y\n")
        if setup.returncode != 0:
            report.record("strict-placeholder", False, "install.sh failed before strict lint could run", setup.stdout, setup.stderr)
            return
        proc = _run([sys.executable, "scripts/wiki_sync.py", "lint", "--strict"], cwd=tmp)
        if proc.returncode == 0:
            report.record(
                "strict-placeholder",
                False,
                "--strict should fail on a fresh install that still has ${...} / YYYY-MM-DD placeholders",
                proc.stdout,
                proc.stderr,
            )
            return
        report.record("strict-placeholder", True, detail="--strict correctly flagged fresh-install placeholders")


def check_example_drift(report: Report) -> None:
    install_sh = REPO_ROOT / "install.sh"
    with tempfile.TemporaryDirectory() as tmp:
        setup = _run(["bash", str(install_sh)], cwd=tmp, input_="y\n")
        if setup.returncode != 0:
            report.record("example-drift", False, "install.sh failed before example drift check", setup.stdout, setup.stderr)
            return

        installed_files = {
            str(path.relative_to(tmp))
            for path in Path(tmp).rglob("*")
            if path.is_file()
        }
    example_root = REPO_ROOT / "example" / "minimal-project"
    example_files = {
        str(path.relative_to(example_root))
        for path in example_root.rglob("*")
        if path.is_file()
    }

    pairs = [
        (REPO_ROOT / "scripts" / "context_hub.py", REPO_ROOT / "example" / "minimal-project" / "scripts" / "context_hub.py"),
        (REPO_ROOT / "scripts" / "wiki_sync.py", REPO_ROOT / "example" / "minimal-project" / "scripts" / "wiki_sync.py"),
    ]
    drift = []
    missing = sorted(installed_files - example_files)
    extra = sorted(example_files - installed_files)
    if missing:
        drift.append("example/minimal-project missing fresh-install files: " + ", ".join(missing))
    extra_allowed = {"README.md"}
    unexpected_extra = [path for path in extra if path not in extra_allowed]
    if unexpected_extra:
        drift.append("example/minimal-project has unexpected extra files: " + ", ".join(unexpected_extra))
    for a, b in pairs:
        if not b.exists():
            drift.append(f"{b.relative_to(REPO_ROOT)} missing")
            continue
        if a.read_bytes() != b.read_bytes():
            drift.append(f"{b.relative_to(REPO_ROOT)} differs from {a.relative_to(REPO_ROOT)}")
    if drift:
        report.record("example-drift", False, "; ".join(drift))
        return
    report.record(
        "example-drift",
        True,
        detail=f"file set matches fresh install ({len(installed_files)} files; README.md allowed) and {len(pairs)} script pair(s) byte-identical",
    )


# ── Entry point ───────────────────────────────────────────────────────────────

ALL_CHECKS = [
    ("pycompile", check_pycompile),
    ("cli-help", check_cli_help),
    ("self-install-ref", check_self_install_refusal),
    ("fresh-install", check_fresh_install),
    ("wiki-lint", check_fresh_install_wiki_lint),
    ("repo-lint", check_repo_lint),
    ("strict-placeholder", check_strict_placeholder_on_fresh_install),
    ("example-drift", check_example_drift),
]


def format_human(report: Report, verbose: bool) -> str:
    lines = []
    for check in report.checks:
        icon = "✅" if check.passed else "❌"
        lines.append(f"  {icon} {check.name:22s} {check.detail}")
        if verbose and (check.stdout or check.stderr):
            if check.stdout.strip():
                lines.append("      stdout:")
                for stdout_line in check.stdout.rstrip().splitlines():
                    lines.append(f"        {stdout_line}")
            if check.stderr.strip():
                lines.append("      stderr:")
                for stderr_line in check.stderr.rstrip().splitlines():
                    lines.append(f"        {stderr_line}")
    passed = sum(1 for c in report.checks if c.passed)
    total = len(report.checks)
    verdict = "ALL GREEN" if report.all_passed else "FAILED"
    lines.append("")
    lines.append(f"  {verdict} — {passed}/{total} checks passed")
    return "\n".join(lines)


def format_json(report: Report) -> str:
    payload = {
        "all_passed": report.all_passed,
        "passed_count": sum(1 for c in report.checks if c.passed),
        "total": len(report.checks),
        "checks": [asdict(c) for c in report.checks],
    }
    return json.dumps(payload, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="OAW harness health check — the same gate CI runs, available locally.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="show raw stdout/stderr for each check")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable JSON summary")
    args = parser.parse_args(argv)

    if shutil.which("bash") is None:
        print("❌ bash is required but not on PATH", file=sys.stderr)
        return 2

    report = Report()
    header = "🔧 OAW harness check"
    if not args.json:
        print(header)
        print("=" * len(header))
    for _, fn in ALL_CHECKS:
        fn(report)

    if args.json:
        print(format_json(report))
    else:
        print(format_human(report, args.verbose))
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
