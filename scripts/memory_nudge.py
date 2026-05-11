#!/usr/bin/env python3
"""memory_nudge — does memory.md need an entry?

A passive, agent-driven reminder. Inspired by Hermes Agent's periodic memory
nudges (run_agent.py:11560+) but adapted to OAW's markdown-first, no-server
architecture: instead of a turn counter inside a running process, we look at
git activity since memory.md was last touched.

Usage:
  python3 scripts/memory_nudge.py check     # exit 0, print nudge if warranted
  python3 scripts/memory_nudge.py status    # always print current state
  python3 scripts/memory_nudge.py --json    # machine-readable form of check

Rules a nudge fires on:
  (a) memory.md hasn't been modified in the last NUDGE_HOURS (default 24).
  (b) Since memory.md's last mtime, git has ≥ NUDGE_COMMITS commits
      (default 3) OR uncommitted-changes ≥ NUDGE_DIRTY_FILES (default 5).
  (c) memory.md doesn't exist yet, but the working tree has activity.

Silent (no output, exit 0) if no nudge is warranted. Agents call this at
session end as part of the self-improving protocol; if something is printed,
the agent reviews and writes an entry.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Repo root resolution mirrors context_hub.py: walk up from this script.
BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_FILE = BASE_DIR / ".agents" / "memory.md"

NUDGE_HOURS = int(os.environ.get("OAW_NUDGE_HOURS", "24"))
NUDGE_COMMITS = int(os.environ.get("OAW_NUDGE_COMMITS", "3"))
NUDGE_DIRTY_FILES = int(os.environ.get("OAW_NUDGE_DIRTY_FILES", "5"))


def _git(args: list[str]) -> str:
    """Run a git command; return stdout (empty string on failure)."""
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return out.stdout if out.returncode == 0 else ""
    except Exception:
        return ""


def _memory_last_mtime() -> float | None:
    if not MEMORY_FILE.exists():
        return None
    return MEMORY_FILE.stat().st_mtime


def _commits_since(ts: float | None) -> list[str]:
    """Recent commit subjects since a unix timestamp (or last 7 days if None)."""
    since_arg = f"--since=@{int(ts)}" if ts else "--since=7.days"
    raw = _git(["log", since_arg, "--pretty=%h %s", "--no-merges", "-n", "20"])
    return [line for line in raw.splitlines() if line.strip()]


def _dirty_files() -> list[str]:
    raw = _git(["status", "--porcelain"])
    return [line for line in raw.splitlines() if line.strip()]


def evaluate() -> dict:
    """Return a structured assessment of whether a nudge should fire."""
    now = time.time()
    last_mtime = _memory_last_mtime()
    age_hours = (now - last_mtime) / 3600 if last_mtime else None

    commits = _commits_since(last_mtime)
    dirty = _dirty_files()

    reasons: list[str] = []
    if last_mtime is None:
        if commits or dirty:
            reasons.append("memory.md does not exist yet — bootstrap with at least one entry")
    else:
        if age_hours is not None and age_hours >= NUDGE_HOURS:
            reasons.append(
                f"memory.md untouched for {age_hours:.1f}h (threshold {NUDGE_HOURS}h)"
            )
        if len(commits) >= NUDGE_COMMITS:
            reasons.append(
                f"{len(commits)} commits since last memory entry (threshold {NUDGE_COMMITS})"
            )
        if len(dirty) >= NUDGE_DIRTY_FILES:
            reasons.append(
                f"{len(dirty)} uncommitted changes (threshold {NUDGE_DIRTY_FILES})"
            )

    should_nudge = bool(reasons)
    return {
        "should_nudge": should_nudge,
        "reasons": reasons,
        "memory_age_hours": age_hours,
        "commits_since_last_entry": commits,
        "dirty_files_count": len(dirty),
        "thresholds": {
            "hours": NUDGE_HOURS,
            "commits": NUDGE_COMMITS,
            "dirty_files": NUDGE_DIRTY_FILES,
        },
    }


def _format_nudge(assessment: dict) -> str:
    """Human-readable nudge text for an agent to act on."""
    lines = [
        "📝 memory.md nudge — recent activity suggests an entry is overdue",
        "",
        "Why:",
    ]
    for r in assessment["reasons"]:
        lines.append(f"  • {r}")
    commits = assessment["commits_since_last_entry"]
    if commits:
        lines.append("")
        lines.append("Commits to consider summarizing:")
        for c in commits[:5]:
            lines.append(f"  - {c}")
        if len(commits) > 5:
            lines.append(f"  …and {len(commits) - 5} more")
    lines.append("")
    lines.append("Suggested action:")
    lines.append('  python3 scripts/context_hub.py memory add "[TAG] One-line summary - details"')
    lines.append("")
    lines.append(
        "Tags: [DECISION] [INSIGHT] [BUG] [FIX] [EXPERIMENT] [ARCHITECTURE] [WORKAROUND] [FEATURE] [REVIEW]"
    )
    return "\n".join(lines)


def cmd_check(emit_json: bool) -> int:
    a = evaluate()
    if emit_json:
        print(json.dumps(a, indent=2))
        return 0
    if not a["should_nudge"]:
        return 0  # silent
    print(_format_nudge(a))
    return 0


def cmd_status() -> int:
    a = evaluate()
    print(f"Thresholds: hours={a['thresholds']['hours']}, "
          f"commits={a['thresholds']['commits']}, dirty={a['thresholds']['dirty_files']}")
    if a["memory_age_hours"] is None:
        print("memory.md: (none yet)")
    else:
        print(f"memory.md age: {a['memory_age_hours']:.1f} hours")
    print(f"Commits since last memory entry: {len(a['commits_since_last_entry'])}")
    print(f"Dirty files: {a['dirty_files_count']}")
    if a["should_nudge"]:
        print("\nNudge: YES")
        for r in a["reasons"]:
            print(f"  - {r}")
    else:
        print("\nNudge: no")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="memory_nudge", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("check", help="print nudge if warranted, otherwise silent")
    sub.add_parser("status", help="always print current state")
    ap.add_argument("--json", action="store_true", help="machine-readable output for check")
    args = ap.parse_args()

    if args.cmd == "status":
        return cmd_status()
    # Default: check
    return cmd_check(emit_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
