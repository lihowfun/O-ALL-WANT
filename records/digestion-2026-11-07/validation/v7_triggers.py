#!/usr/bin/env python3
"""V7: retrospective check of the D31 mode triggers against SZZ bug-introducing labels.

Preregistered in PREREG.md, section "V7 D31 觸發條件的回溯驗證". Spends no model tokens.

1. Commits: every non-merge commit reachable from local branches and remote-tracking
   branches of the repository, deduplicated.
2. Bug-fixing commits: the full message matches FIX_REGEX (case-insensitive) and the
   commit touches at least one code file (see is_code).
3. SZZ: for each bug-fixing commit, the lines it deleted or modified in code files are
   blamed with `git blame -w` on its parent; the blamed commits are "bug-introducing".
4. Mode: `scripts/oaw_mode.py suggest --range <c>^..<c> --json` for every commit, run
   from the tool checkout given by --tool-root (claude/oaw-2 at 8e607f0 per PREREG).
5. Mode x bug-introducing tables, relative risk, one-sided Fisher exact p, the share of
   commits flagged deep, and the PREREG reading rule.

Standard library only. Usage:
  python3 v7_triggers.py --repo <git checkout> --tool-root <OAW-v2 checkout> [--out FILE]
The JSON holds commit shas, repo-relative paths and sanitized subjects only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import getpass
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path, PurePosixPath

FIX_REGEX = r"fix|bug|regress|revert|hotfix|broken|crash|wrong"
FIX = re.compile(FIX_REGEX, re.IGNORECASE)
# Sensitivity only (not preregistered): whole words in the subject line, so that
# "debug", "prefix", "suffix" and "fixture" do not count.
FIX_STRICT_REGEX = (r"\b(?:fix(?:e[sd]|ing)?|bug(?:s|fix(?:es)?)?|regress(?:ion|ions|ed|es)?|"
                    r"revert(?:s|ed)?|hotfix(?:es)?|broken|crash(?:es|ed|ing)?|wrong)\b")
FIX_STRICT = re.compile(FIX_STRICT_REGEX, re.IGNORECASE)

CODE_SUFFIXES = {".py", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
                 ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".html", ".css"}
DOC_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ".adoc"}
CODE_RULE = ("code file = not a test file, not a doc (.md .markdown .rst .txt .adoc), and either a "
             "source/script extension (" + " ".join(sorted(CODE_SUFFIXES)) + ") or a CI workflow "
             "(.github/workflows/*.yml|*.yaml). Everything else (json, jsonl, other yaml such as skill "
             "agent configs and issue templates, svg/png/zip, LICENSE, sha256, .gitignore, "
             ".cursorrules/.windsurfrules) is treated as data/config, not code.")
TEST_RULE = ("test file = any directory component named tests or test, or a file named test_*, "
             "conftest.py, *_test.*, *.test.* or *.spec.*")
READ_RATIO, READ_P = 1.5, 0.05
BLAME_CHUNK = 100


class StepError(Exception):
    pass


def git(repo: Path, *args: str) -> bytes:
    command = ["git", "-C", str(repo), "-c", "core.quotepath=false", *args]
    process = subprocess.run(command, input=b"", capture_output=True, check=False)
    if process.returncode:
        raise StepError(f"git {' '.join(args[:3])} failed: "
                        + process.stderr.decode("utf-8", "replace").strip()[-400:])
    return process.stdout


def is_test(path: str) -> bool:
    parts = path.split("/")
    name = parts[-1].lower()
    return (any(part.lower() in ("tests", "test") for part in parts[:-1]) or name.startswith("test_")
            or name == "conftest.py" or re.search(r"(?:_test|\.test|\.spec)\.[^.]+$", name) is not None)


def is_code(path: str) -> bool:
    if is_test(path):
        return False
    suffix = PurePosixPath(path).suffix.lower()
    if suffix in DOC_SUFFIXES:
        return False
    if suffix in CODE_SUFFIXES:
        return True
    return path.startswith(".github/workflows/") and suffix in (".yml", ".yaml")


def name_status(repo: Path, base: str, commit: str) -> list[dict]:
    data = git(repo, "diff", "--name-status", "-z", "--find-renames", "--no-ext-diff", base, commit, "--")
    tokens = [t.decode("utf-8", "surrogateescape") for t in data.split(b"\0")]
    entries, index = [], 0
    while index < len(tokens) and tokens[index]:
        status = tokens[index][:1]
        if status in ("R", "C"):
            entries.append({"status": status, "old": tokens[index + 1], "new": tokens[index + 2]})
            index += 3
        else:
            entries.append({"status": status, "old": tokens[index + 1], "new": tokens[index + 1]})
            index += 2
    return entries


HUNK = re.compile(rb"^@@ -(\d+)(?:,(\d+))? \+")


def deleted_ranges(repo: Path, parent: str, fix: str, entry: dict) -> tuple[list[tuple[int, int]], list[str]]:
    """Parent-side line ranges that the fix deleted or modified in one file."""
    warnings = []
    if entry["status"] == "R":
        out = git(repo, "diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv", "--find-renames",
                  parent, fix, "--", entry["old"], entry["new"])
        if b"\nrename from " not in b"\n" + out:
            warnings.append(f"rename {entry['old']} -> {entry['new']} not re-detected in the per-file diff")
    else:
        out = git(repo, "diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv", "--no-renames",
                  parent, fix, "--", entry["old"])
    ranges = []
    for line in out.split(b"\n"):
        match = HUNK.match(line)
        if match:
            start, count = int(match.group(1)), int(match.group(2) or b"1")
            if count:
                ranges.append((start, start + count - 1))
    return ranges, warnings


BLAME_HEADER = re.compile(rb"^([0-9a-f]{40,64}) \d+ \d+")


def blame(repo: Path, parent: str, path: str, ranges: list[tuple[int, int]]) -> Counter:
    counts: Counter = Counter()
    for offset in range(0, len(ranges), BLAME_CHUNK):
        args = ["blame", "-w", "--porcelain"]
        for start, end in ranges[offset:offset + BLAME_CHUNK]:
            args += ["-L", f"{start},{end}"]
        for line in git(repo, *args, parent, "--", path).split(b"\n"):
            match = BLAME_HEADER.match(line)
            if match:
                counts[match.group(1).decode()] += 1
    return counts


def fisher_greater(a: int, b: int, c: int, d: int) -> float:
    """One-sided Fisher exact p: P(X >= a) for the top-left cell, margins fixed."""
    n1, total, events = a + b, a + b + c + d, a + c
    denominator = math.comb(total, n1)
    numerator = sum(math.comb(events, x) * math.comb(total - events, n1 - x)
                    for x in range(a, min(n1, events) + 1))
    return numerator / denominator


def compare(name: str, group: Counter, reference: Counter) -> dict:
    a, n1 = group["bug"], group["n"]
    c, n2 = reference["bug"], reference["n"]
    rate1 = a / n1 if n1 else None
    rate2 = c / n2 if n2 else None
    if rate1 is None or rate2 is None:
        rr, rr_text = None, "undefined (empty group)"
    elif rate2 == 0:
        rr, rr_text = None, "infinite" if a else "undefined (0/0)"
    else:
        rr = rate1 / rate2
        rr_text = f"{rr:.3f}"
    p = fisher_greater(a, n1 - a, c, n2 - c) if n1 and n2 else None
    if rr_text == "infinite":
        ratio_ok, ratio_le_1 = True, False
    elif rr is None:
        ratio_ok, ratio_le_1 = False, False
    else:
        ratio_ok, ratio_le_1 = rr >= READ_RATIO, rr <= 1
    if ratio_ok and p is not None and p < READ_P:
        reading = "predictive"
    elif ratio_le_1:
        reading = "not validated"
    else:
        reading = "undetermined"
    return {"comparison": name, "group": {"n": n1, "bug_introducing": a, "rate": rate1},
            "reference": {"n": n2, "bug_introducing": c, "rate": rate2},
            "relative_risk": rr, "relative_risk_text": rr_text, "fisher_one_sided_p": p, "reading": reading}


def analyse(units: list[dict], label_key: str) -> dict:
    cells = {mode: Counter() for mode in ("deep", "standard", "light")}
    for unit in units:
        cells[unit["mode"]]["n"] += 1
        cells[unit["mode"]]["bug"] += int(unit[label_key])
    merged = cells["deep"] + cells["standard"]
    total = sum(cell["n"] for cell in cells.values())
    bugs = sum(cell["bug"] for cell in cells.values())
    sizes = {mode: [u["suggest"]["code_lines"] for u in units if u["mode"] == mode] for mode in cells}
    table = {mode: {"n": cell["n"], "bug_introducing": cell["bug"], "not_bug_introducing": cell["n"] - cell["bug"],
                    "bug_rate": (cell["bug"] / cell["n"]) if cell["n"] else None,
                    "median_suggest_code_lines": statistics.median(sizes[mode]) if sizes[mode] else None}
             for mode, cell in cells.items()}
    distribution = {
        "bug_introducing": {mode: (cells[mode]["bug"] / bugs if bugs else None) for mode in cells},
        "other": {mode: ((cells[mode]["n"] - cells[mode]["bug"]) / (total - bugs) if total - bugs else None)
                  for mode in cells},
    }
    comparisons = [compare("deep vs light", cells["deep"], cells["light"]),
                   compare("standard vs light", cells["standard"], cells["light"]),
                   compare("deep+standard vs light", merged, cells["light"]),
                   compare("deep vs not deep", cells["deep"], cells["standard"] + cells["light"])]
    governing = [c for c in comparisons if c["comparison"] in ("deep vs light", "deep+standard vs light")]
    if any(c["reading"] == "predictive" for c in governing):
        overall = "predictive"
    elif all(c["reading"] == "not validated" for c in governing):
        overall = "not validated"
    else:
        overall = "undetermined"
    return {"units": total, "bug_introducing": bugs, "table": table,
            "mode_share_within": distribution, "comparisons": comparisons,
            "review_burden": {"deep_share": cells["deep"]["n"] / total if total else None,
                              "deep_or_standard_share": merged["n"] / total if total else None},
            "reading": overall}


def tool_provenance(tool_root: Path, script: Path) -> dict:
    head = git(tool_root, "rev-parse", "HEAD").decode().strip()
    branch = git(tool_root, "rev-parse", "--abbrev-ref", "HEAD").decode().strip()
    blob_head = git(tool_root, "rev-parse", "HEAD:scripts/oaw_mode.py").decode().strip()
    blob_file = git(tool_root, "hash-object", str(script)).decode().strip()
    dirty = [line for line in git(tool_root, "status", "--porcelain").decode().splitlines() if line]
    settings = [name for name in ("settings.json", "settings.local.json") if (tool_root / ".claude" / name).is_file()]
    sys.dont_write_bytecode = True  # do not leave a .pyc in the tool checkout
    spec = importlib.util.spec_from_file_location("oaw_mode_v7", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    hooked = sorted(module.hook_files(tool_root))
    return {"script": "scripts/oaw_mode.py", "checkout_branch": branch, "checkout_head": head,
            "script_blob_at_head": blob_head, "script_blob_on_disk": blob_file,
            "script_matches_head": blob_head == blob_file, "checkout_dirty_entries": len(dirty),
            "project_settings_files_present": [f".claude/{name}" for name in settings],
            "hook_derived_harness_paths": hooked,
            "thresholds": {"standard_lines": module.STANDARD_LINES, "standard_files": module.STANDARD_FILES,
                           "deep_deleted_files": module.DEEP_DELETED_FILES}}


# Tool and service identities that appear as authors but are not personal names.
TOOL_IDENTITIES = {"github", "codex", "claude", "noreply", "noreply@github.com", "codex@openai.com"}


def private_tokens(repo: Path) -> list[str]:
    """Personal names and emails that must not appear in the JSON."""
    data = git(repo, "log", "--branches", "--remotes", "--format=%an%x00%ae%x00%cn%x00%ce").decode("utf-8", "replace")
    tokens = set()
    for line in data.splitlines():
        for value in line.split("\0"):
            value = value.strip()
            if not value or value.lower() in TOOL_IDENTITIES:
                continue
            tokens.add(value)
            if "@" in value:
                local = value.split("@", 1)[0].split("+", 1)[-1]
                if local.lower() not in TOOL_IDENTITIES:
                    tokens.add(local)
            else:
                tokens.update(part for part in re.split(r"\s+", value) if len(part) >= 3)
    tokens.add(getpass.getuser())
    return sorted((t for t in tokens if len(t) >= 3 and t.lower() not in TOOL_IDENTITIES), key=len, reverse=True)


def word(token: str) -> re.Pattern:
    return re.compile(r"(?<![\w])" + re.escape(token) + r"(?![\w])", re.IGNORECASE)


EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
ABSOLUTE = re.compile(r"(?<![\w.])(?:/(?:mnt|home|tmp|Users|root|var|opt|usr|etc)/|[A-Za-z]:\\)")


def sanitize(text: str, tokens: list[str]) -> str:
    text = EMAIL.sub("[email]", text)
    text = ABSOLUTE.sub("[abs-path]/", text)
    for token in tokens:
        text = word(token).sub("[name]", text)
    return text


def leak_scan(text: str, tokens: list[str], extra: list[str]) -> list[str]:
    found = []
    if EMAIL.search(text):
        found.append("email:" + EMAIL.search(text).group(0)[:3] + "...")
    if ABSOLUTE.search(text):
        found.append("absolute path")
    for token in tokens:
        if word(token).search(text):
            found.append("name token of length %d" % len(token))
    lowered = text.lower()
    for value in extra:
        if value and value.lower() in lowered:
            found.append("local path of length %d" % len(value))
    return found


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=str(here), help="the git repository to read (default: this file's repo)")
    parser.add_argument("--tool-root", required=True, help="checkout holding scripts/oaw_mode.py (claude/oaw-2)")
    parser.add_argument("--out", default=str(here / "v7_triggers.json"))
    args = parser.parse_args()
    repo = Path(git(Path(args.repo), "rev-parse", "--show-toplevel").decode().strip())
    tool_root = Path(args.tool_root).resolve()
    tool_script = tool_root / "scripts" / "oaw_mode.py"
    tokens = private_tokens(repo)
    extra_leaks = sorted({str(Path.home()), str(repo), str(tool_root), str(here)}, key=len, reverse=True)

    provenance = tool_provenance(tool_root, tool_script)
    prereg = here / "PREREG.md"
    prereg_sha = hashlib.sha256(prereg.read_bytes()).hexdigest() if prereg.is_file() else None

    # 1. The commit universe.
    refs = []
    for line in git(repo, "for-each-ref", "--format=%(refname)%00%(objectname)%00%(symref)",
                    "refs/heads", "refs/remotes").decode().splitlines():
        name, sha, symref = line.split("\0")
        refs.append({"ref": name, "sha": sha, "symbolic_to": symref or None})
    log = git(repo, "log", "--no-merges", "--branches", "--remotes", "--date-order",
              "--format=%H%x00%P%x00%ad%x00%s%x00%B%x1e", "--date=short").decode("utf-8", "replace")
    commits = {}
    for record in log.split("\x1e"):
        record = record.lstrip("\n")
        if not record:
            continue
        sha, parents, date, subject, body = record.split("\0", 4)
        commits[sha] = {"sha": sha, "parents": parents.split(), "date": date, "subject": subject, "message": body}
    local_only = set(git(repo, "rev-list", "--no-merges", "--branches").decode().split())
    non_records_refs = [r["ref"] for r in refs if not r["ref"].endswith("/records") and not r["symbolic_to"]]
    outside_records = set(git(repo, "rev-list", "--no-merges", *non_records_refs).decode().split())
    empty_tree = git(repo, "hash-object", "-t", "tree", "--stdin").decode().strip()
    roots = sorted(sha for sha, c in commits.items() if not c["parents"])

    # 2. Files touched and the fix labels.
    for sha, commit in commits.items():
        base = commit["parents"][0] if commit["parents"] else empty_tree
        commit["entries"] = name_status(repo, base, sha)
        paths = {p for e in commit["entries"] for p in (e["old"], e["new"])}
        commit["code_paths"] = sorted(p for p in paths if is_code(p))
        commit["fix_keywords"] = sorted({m.group(0).lower() for m in FIX.finditer(commit["message"])})
        commit["fix_primary"] = bool(commit["fix_keywords"]) and bool(commit["code_paths"])
        commit["fix_strict"] = bool(FIX_STRICT.search(commit["subject"])) and bool(commit["code_paths"])
        commit["records_only"] = sha not in outside_records

    # 3. SZZ on every commit that either fix rule labels.
    fixes, warnings, blame_failures = {}, [], []
    for sha, commit in commits.items():
        if not (commit["fix_primary"] or commit["fix_strict"]):
            continue
        if not commit["parents"]:
            warnings.append(f"{sha}: fix-labelled root commit, nothing to blame")
            continue
        parent = commit["parents"][0]
        blamed, files, deleted_lines = Counter(), [], 0
        for entry in commit["entries"]:
            if entry["status"] not in ("M", "R", "D", "T") or not is_code(entry["old"]):
                continue
            try:
                ranges, notes = deleted_ranges(repo, parent, sha, entry)
                warnings.extend(f"{sha}: {note}" for note in notes)
                if not ranges:
                    continue
                counts = blame(repo, parent, entry["old"], ranges)
            except StepError as exc:
                blame_failures.append({"fix": sha, "path": entry["old"], "error": sanitize(str(exc), tokens)})
                continue
            lines = sum(end - start + 1 for start, end in ranges)
            deleted_lines += lines
            blamed.update(counts)
            files.append({"path": entry["old"], "status": entry["status"], "deleted_or_modified_lines": lines,
                          "blamed_lines": sum(counts.values())})
        fixes[sha] = {"fix": sha, "parent": parent, "primary": commit["fix_primary"], "strict": commit["fix_strict"],
                      "files": files, "deleted_or_modified_code_lines": deleted_lines, "blamed": dict(blamed)}

    # Exclusions: the initial import (root commit) is neither an analysis unit nor a
    # bug-introducing target in the primary analysis; blamed shas outside the universe
    # (merge commits) cannot be units and are dropped.
    excluded_targets = set(roots)
    dropped_outside = Counter()
    blamed_by = {"primary": {}, "strict": {}}
    root_blamed_by = {"primary": set(), "strict": set()}
    for fix in fixes.values():
        for variant in ("primary", "strict"):
            if not fix[variant]:
                continue
            for target in fix["blamed"]:
                if target not in commits:
                    dropped_outside[target] += 1
                    continue
                if target in excluded_targets:
                    root_blamed_by[variant].add(fix["fix"])
                blamed_by[variant].setdefault(target, set()).add(fix["fix"])

    # 4. Mode for every commit.
    skipped = []
    for sha, commit in commits.items():
        base = f"{sha}^" if commit["parents"] else empty_tree
        command = [sys.executable, str(tool_script), "suggest", "--root", str(tool_root),
                   "--range", f"{base}..{sha}", "--json"]
        process = subprocess.run(command, capture_output=True, check=False)
        if process.returncode:
            commit["mode"] = None
            skipped.append({"sha": sha, "reason": "suggest exit %d: %s" % (
                process.returncode, sanitize(process.stderr.decode("utf-8", "replace").strip()[-300:], tokens))})
            continue
        result = json.loads(process.stdout)
        commit["mode"] = result["mode"]
        commit["suggest"] = {"range": "<empty-tree>..%s" % sha if not commit["parents"] else f"{sha}^..{sha}",
                             "files": result["files"], "code_files": result["code_files"],
                             "code_lines": result["code_lines"], "deleted_files": result["deleted_files"],
                             "triggers": [{"mode": t["mode"], "rule": t["rule"], "paths": len(t["paths"])}
                                          for t in result["triggers"]],
                             "reasons": result["reasons"]}

    for commit in commits.values():
        commit["bug_introducing_primary"] = commit["sha"] in blamed_by["primary"]
        commit["bug_introducing_strict"] = commit["sha"] in blamed_by["strict"]

    # 5. Analyses.
    usable = [c for c in commits.values() if c["mode"] is not None]
    primary_units = [c for c in usable if c["sha"] not in excluded_targets]
    analyses = {
        "primary": analyse(primary_units, "bug_introducing_primary"),
        "sens_root_included": analyse(usable, "bug_introducing_primary"),
        "sens_strict_fix_regex": analyse(primary_units, "bug_introducing_strict"),
        "sens_code_touching_only": analyse([c for c in primary_units if c["code_paths"]], "bug_introducing_primary"),
        "sens_without_records_only": analyse([c for c in primary_units if not c["records_only"]],
                                             "bug_introducing_primary"),
        # Size held below the standard threshold: only deep triggers separate deep from light here.
        "sens_small_code_changes": analyse([c for c in primary_units if c["code_paths"] and not any(
            t["rule"] == "size" for t in c["suggest"]["triggers"])], "bug_introducing_primary"),
    }
    rules = Counter()
    rule_bug = Counter()
    for commit in primary_units:
        for rule in sorted({t["rule"] for t in commit["suggest"]["triggers"]}):
            rules[rule] += 1
            rule_bug[rule] += int(commit["bug_introducing_primary"])
    by_rule = {rule: {"n": rules[rule], "bug_introducing": rule_bug[rule],
                      "bug_rate": rule_bug[rule] / rules[rule]} for rule in sorted(rules)}

    top_blamed = sorted(blamed_by["primary"].items(), key=lambda item: (-len(item[1]), item[0]))[:15]
    result = {
        "experiment": "V7 D31 trigger retrospective validation",
        "prereg": {"file": "PREREG.md", "section": "V7 D31 觸發條件的回溯驗證（不花 token）", "sha256": prereg_sha},
        "generated": dt.date.today().isoformat(),
        "environment": {"python": platform.python_version(),
                        "git": git(repo, "--version").decode().strip()},
        "tool": provenance,
        "data": {
            "refs": refs,
            "non_merge_commits": len(commits),
            "non_merge_commits_local_branches_only": len(local_only),
            "added_by_remote_tracking": len(set(commits) - local_only),
            "root_commits": roots,
            "records_only_commits": sum(c["records_only"] for c in commits.values()),
        },
        "rules": {
            "fix_regex": FIX_REGEX, "fix_regex_flags": "case-insensitive, substring search over the full message",
            "fix_strict_regex_sensitivity": FIX_STRICT_REGEX + "  (subject line only; not preregistered)",
            "code_file": CODE_RULE, "test_file": TEST_RULE,
            "szz": ("for each fix commit: per file whose parent-side path is a code file and whose status is "
                    "M, R, D or T, take `git diff -U0` parent..fix hunks; every parent-side line in a hunk with "
                    "a non-zero old count is a deleted-or-modified line; blame those lines with "
                    "`git blame -w --porcelain -L ...` at the parent (default rename following, no -M/-C). "
                    "Pure additions blame nothing. Whole-file deletions are included."),
            "excluded_targets": {"shas": sorted(excluded_targets),
                                 "reason": "root commit = initial import; also not an analysis unit in the primary "
                                           "analysis because its diff is against the empty tree"},
            "dropped_blamed_outside_universe": dict(dropped_outside),
            "reading": (f"per comparison: RR >= {READ_RATIO} and one-sided Fisher p < {READ_P} -> predictive; "
                        "RR <= 1 -> not validated; else undetermined. Overall: predictive if 'deep vs light' or "
                        "'deep+standard vs light' is predictive; not validated if both are; else undetermined."),
        },
        "counts": {
            "fix_commits_primary": sum(c["fix_primary"] for c in commits.values()),
            "fix_commits_strict": sum(c["fix_strict"] for c in commits.values()),
            "message_matches_without_code": sum(bool(c["fix_keywords"]) and not c["code_paths"]
                                                 for c in commits.values()),
            "fix_commits_primary_with_blamed_lines": sum(1 for f in fixes.values() if f["primary"] and f["blamed"]),
            "fix_commits_primary_additions_only": sum(1 for f in fixes.values()
                                                      if f["primary"] and not f["deleted_or_modified_code_lines"]),
            "bug_introducing_primary_in_universe": len(blamed_by["primary"]),
            "bug_introducing_primary_excluding_targets": len(set(blamed_by["primary"]) - excluded_targets),
            "bug_introducing_strict_excluding_targets": len(set(blamed_by["strict"]) - excluded_targets),
            "fixes_blaming_root_primary": len(root_blamed_by["primary"]),
            "suggest_skipped": len(skipped),
            "blame_failures": len(blame_failures),
        },
        "analyses": analyses,
        "analysis_notes": {
            "primary": "preregistered analysis; root commit excluded as unit and as blame target",
            "sens_root_included": "not preregistered: root commit kept as unit and target",
            "sens_strict_fix_regex": "not preregistered: fix label from FIX_STRICT_REGEX on the subject only",
            "sens_code_touching_only": "not preregistered: only commits that touch a code file (others cannot be "
                                       "bug-introducing by construction)",
            "sens_without_records_only": "not preregistered: drops commits reachable only from the records branch",
            "sens_small_code_changes": "not preregistered: code-touching commits without the size trigger, so "
                                       "deep vs light reflects the deep triggers, not change size",
        },
        "by_trigger_rule_primary_units": by_rule,
        "top_blamed_primary": [{"sha": sha, "fixes": len(fixers), "subject": sanitize(commits[sha]["subject"], tokens),
                                "mode": commits[sha]["mode"]} for sha, fixers in top_blamed],
        "skipped": skipped,
        "blame_failures": blame_failures,
        "warnings": [sanitize(w, tokens) for w in warnings],
        "commits": [{"sha": c["sha"], "date": c["date"], "subject": sanitize(c["subject"], tokens),
                     "root": not c["parents"], "records_only": c["records_only"], "code_paths": c["code_paths"],
                     "fix_keywords": c["fix_keywords"], "fix_primary": c["fix_primary"], "fix_strict": c["fix_strict"],
                     "bug_introducing_primary": c["bug_introducing_primary"],
                     "bug_introducing_strict": c["bug_introducing_strict"],
                     "blamed_by_primary": sorted(blamed_by["primary"].get(c["sha"], ())),
                     "mode": c["mode"], "suggest": c.get("suggest")} for c in commits.values()],
        "fixes": list(fixes.values()),
    }
    text = json.dumps(result, indent=1, ensure_ascii=False)
    leaks = leak_scan(text, tokens, extra_leaks)
    if leaks:
        print("refusing to write: private data found in the output: " + ", ".join(leaks), file=sys.stderr)
        return 1
    Path(args.out).write_text(text + "\n", encoding="utf-8")
    p = analyses["primary"]
    print(f"commits={len(commits)} units={p['units']} bug_introducing={p['bug_introducing']} "
          f"fix_primary={result['counts']['fix_commits_primary']} skipped={len(skipped)} reading={p['reading']}")
    for mode, cell in p["table"].items():
        print(f"  {mode:8s} n={cell['n']:4d} bug={cell['bug_introducing']:3d} rate={cell['bug_rate']}")
    for comp in p["comparisons"]:
        print(f"  {comp['comparison']:24s} RR={comp['relative_risk_text']} p={comp['fisher_one_sided_p']} "
              f"-> {comp['reading']}")
    print(f"  deep share={p['review_burden']['deep_share']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
