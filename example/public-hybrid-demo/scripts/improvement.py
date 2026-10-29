#!/usr/bin/env python3
"""Opt-in, evidence-linked improvement proposals. Never applies a patch."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

from oaw_common import confined_path, locked_update

SCHEMA = 1
MATCHED_FIELDS = ("model", "effort", "host", "host_version", "environment")
METRICS = ("tokens", "latency_ms", "cost_usd")


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative_path(value):
    path = Path(value)
    if not value or path.is_absolute() or path.drive or "\\" in value or ":" in value or re.search(r"[\x00-\x1f]", value):
        raise ValueError(f"Expected a portable project-relative path: {value!r}")
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError(f"Unsafe relative path: {value!r}")
    return path.as_posix()


def project_path(base, value):
    return Path(confined_path(base, relative_path(value)))


def read_json(path):
    data = Path(path).read_bytes()
    if len(data) > 2_000_000:
        raise ValueError("JSON artifact exceeds the 2 MB limit")
    result = json.loads(data.decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")
    return result, digest(data)


def names(value, label, minimum=1):
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"{label} requires at least {minimum} entries")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} entries must be nonempty strings")
    if len(set(value)) != len(value):
        raise ValueError(f"{label} contains duplicates")
    return value


def number(value, label, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a nonnegative number")
    if not math.isfinite(value) or value < 0 or (integer and not isinstance(value, int)):
        raise ValueError(f"{label} must be a finite nonnegative {'integer' if integer else 'number'}")
    return value


def validate_spec(spec):
    if spec.get("schema_version") != SCHEMA:
        raise ValueError("Unsupported evaluation schema_version")
    if not isinstance(spec.get("id"), str) or not spec["id"].strip():
        raise ValueError("Evaluation id is required")
    names(spec.get("cases"), "cases", minimum=2)
    names(spec.get("assertions"), "assertions")
    names(spec.get("required_checks"), "required_checks")
    repeats = spec.get("repeats")
    if isinstance(repeats, bool) or not isinstance(repeats, int) or not 3 <= repeats <= 100:
        raise ValueError("Evaluation repeats must be between 3 and 100")
    if len(spec["cases"]) * repeats > 10000:
        raise ValueError("Evaluation is too large")
    for field, default in (("minimum_improvement", 0.05), ("maximum_resource_regression", 0.10)):
        value = number(spec.get(field, default), field)
        if value > 1:
            raise ValueError(f"{field} must be a fraction between 0 and 1")
    return spec


def candidate_file(base, candidate_id):
    if not re.fullmatch(r"[a-f0-9]{12}", candidate_id):
        raise ValueError("Invalid candidate id")
    return project_path(base, f".oaw/improvements/{candidate_id}.json")


def load_candidate(base, candidate_id):
    result, _ = read_json(candidate_file(base, candidate_id))
    if result.get("schema_version") != SCHEMA or result.get("id") != candidate_id:
        raise ValueError("Invalid candidate record")
    validate_spec(result.get("evaluation", {}))
    return result


def record(base, candidate_id, mutate, initial=None):
    path = candidate_file(base, candidate_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    def update(text):
        value = json.loads(text) if text.strip() else initial
        if not isinstance(value, dict):
            raise ValueError("Candidate record is missing or invalid")
        mutate(value)
        return json.dumps(value, indent=2, ensure_ascii=False) + "\n"

    locked_update(path, update, default="", root=base)


HUNK = re.compile(r"@@ -[0-9]+(?:,([0-9]+))? \+[0-9]+(?:,([0-9]+))? @@")
EXTENDED = re.compile(r"index [0-9a-f]+\.\.[0-9a-f]+(?: 100(?:644|755))?|(?:old|new|new file|deleted file) mode 100(?:644|755)")


def patch_name(value, prefix):
    value = value.split("\t", 1)[0]
    if value == "/dev/null":
        return None
    if not value.startswith(prefix):
        raise ValueError(f"Patch file header must be /dev/null or start with {prefix}: {value!r}")
    return relative_path(value[len(prefix):])


def patch_paths(text):
    lines = text.split("\n")
    if lines.pop():
        raise ValueError("Patch must end with a newline")
    lines = [line[:-1] if line.endswith("\r") else line for line in lines]
    index = next((number for number, line in enumerate(lines) if line.strip()), len(lines))
    if index == len(lines):
        raise ValueError("Patch must be a git text diff with diff --git headers")
    paths = set()
    while index < len(lines):
        header = lines[index]
        if not header.startswith("diff --git "):
            raise ValueError(f"Unexpected patch line {index + 1}: {header[:80]!r}")
        start = index = index + 1
        while index < len(lines) and EXTENDED.fullmatch(lines[index]):
            index += 1
        extended = lines[start:index]
        if index + 1 >= len(lines) or not lines[index].startswith("--- ") or not lines[index + 1].startswith("+++ "):
            raise ValueError(f"Unsupported patch header at line {index + 1}; only regular-file text edits without renames or copies are allowed")
        old, new = patch_name(lines[index][4:], "a/"), patch_name(lines[index + 1][4:], "b/")
        path = old or new
        if (not path or (old and new and old != new) or header != f"diff --git a/{path} b/{path}"
                or (old is None) != any(line.startswith("new file ") for line in extended)
                or (new is None) != any(line.startswith("deleted file ") for line in extended)):
            raise ValueError(f"Inconsistent patch file headers at line {start}")
        index += 2
        hunks = 0
        while index < len(lines) and lines[index].startswith("@@"):
            match = HUNK.match(lines[index])
            if not match:
                raise ValueError(f"Invalid hunk header at line {index + 1}")
            old_count, new_count, changed = int(match[1] or 1), int(match[2] or 1), False
            index += 1
            while old_count or new_count:
                if index == len(lines):
                    raise ValueError("Patch ends inside a hunk")
                line = lines[index]
                index += 1
                if line.startswith("\\ "):
                    continue
                if line[:1] not in ("", " ", "-", "+"):
                    raise ValueError(f"Corrupt hunk line {index}: {line[:80]!r}")
                old_count -= line[:1] != "+"
                new_count -= line[:1] != "-"
                changed |= line[:1] in ("-", "+")
                if old_count < 0 or new_count < 0:
                    raise ValueError(f"Hunk line counts do not match at line {index}")
            if index < len(lines) and lines[index].startswith("\\ "):
                index += 1
            if not changed:
                raise ValueError(f"Patch hunk ending at line {index} changes no lines")
            hunks += 1
        if not hunks:
            raise ValueError("Every patch section must contain a text hunk")
        paths.add(path)
    return paths


def propose(base, args):
    target = relative_path(args.target)
    project_path(base, target)
    patch_path = project_path(base, args.patch)
    patch = patch_path.read_bytes()
    if len(patch) > 1_000_000:
        raise ValueError("Patch exceeds the 1 MB limit")
    for touched in patch_paths(patch.decode("utf-8")):
        project_path(base, touched)
        if touched != target and not touched.startswith(target + "/"):
            raise ValueError(f"Patch path {touched!r} is outside declared target {target!r}")
        if touched.startswith(".oaw/"):
            raise ValueError("Improvement state cannot be the target of its own patch")
    spec, spec_hash = read_json(project_path(base, args.evaluation))
    validate_spec(spec)
    if not args.snapshot.strip() or not args.title.strip() or not args.hypothesis.strip():
        raise ValueError("Title, hypothesis and base snapshot must be nonempty")
    candidate_id = uuid.uuid4().hex[:12]
    value = {
        "schema_version": SCHEMA,
        "id": candidate_id,
        "title": args.title,
        "hypothesis": args.hypothesis,
        "target": target,
        "base_snapshot": args.snapshot,
        "patch": {"source": relative_path(args.patch), "sha256": digest(patch), "text": patch.decode("utf-8")},
        "evaluation": spec,
        "evaluation_source": relative_path(args.evaluation),
        "evaluation_sha256": spec_hash,
        "created_at": timestamp(),
        "status": "proposed",
        "comparisons": [],
        "decisions": [],
    }
    record(base, candidate_id, lambda current: None, initial=value)
    return {"id": candidate_id, "status": "proposed", "record": f".oaw/improvements/{candidate_id}.json", "patch_applied": False}


def validate_run(base, run, proposal, variant):
    spec = proposal["evaluation"]
    if run.get("schema_version") != SCHEMA or run.get("variant") != variant:
        raise ValueError(f"Invalid {variant} run schema or variant")
    if run.get("evaluation_id") != spec["id"] or run.get("base_snapshot") != proposal["base_snapshot"]:
        raise ValueError(f"{variant} evaluation or base snapshot differs from proposal")
    if not isinstance(run.get("run_id"), str) or not run["run_id"].strip():
        raise ValueError(f"{variant} run_id is required")
    for field in MATCHED_FIELDS:
        if not isinstance(run.get(field), str) or not run[field].strip():
            raise ValueError(f"{variant} run is missing {field}")
    expected_patch = proposal["patch"]["sha256"] if variant == "candidate" else None
    if run.get("patch_sha256") != expected_patch:
        raise ValueError(f"{variant} patch hash does not match")
    checks = run.get("checks")
    if not isinstance(checks, dict) or any(type(checks.get(name)) is not bool for name in spec["required_checks"]):
        raise ValueError(f"{variant} required checks are missing or not boolean")
    cases = run.get("cases")
    if not isinstance(cases, list):
        raise ValueError(f"{variant} cases must be a list")
    expected = {(case, repeat) for case in spec["cases"] for repeat in range(1, spec["repeats"] + 1)}
    seen = set()
    rows = {}
    totals = {name: 0 for name in METRICS}
    evidence = {}
    for case in cases:
        if not isinstance(case, dict) or type(case.get("repeat")) is not int:
            raise ValueError(f"{variant} invalid case record")
        key = (case.get("case_id"), case["repeat"])
        if key not in expected or key in seen:
            raise ValueError(f"{variant} duplicate or unexpected case/repeat: {key}")
        seen.add(key)
        assertions = case.get("assertions")
        if not isinstance(assertions, dict) or any(type(assertions.get(name)) is not bool for name in spec["assertions"]):
            raise ValueError(f"{variant} case assertions are missing or not boolean")
        rows[key] = {name: assertions[name] for name in spec["assertions"]}
        refs = names(case.get("evidence"), "case evidence")
        for ref in refs:
            path = project_path(base, ref)
            if not path.is_file():
                raise ValueError(f"Missing evidence artifact: {ref}")
            evidence[ref] = digest(path.read_bytes())
        for metric in METRICS:
            totals[metric] += number(case.get(metric), metric, integer=metric == "tokens")
    if seen != expected:
        raise ValueError(f"{variant} run does not cover the fixed evaluation cases/repeats")
    successes = sum(all(assertions.values()) for assertions in rows.values())
    return {"passed": successes, "total": len(rows), "metrics": totals, "evidence": evidence, "rows": rows}


def compare(base, args, *, persist=True, proposal=None):
    proposal = proposal or load_candidate(base, args.id)
    if proposal["status"] in ("accepted", "rejected"):
        raise ValueError("Decided proposals are immutable; create a new proposal")
    baseline_path = relative_path(args.baseline)
    candidate_path = relative_path(args.candidate)
    if baseline_path == candidate_path:
        raise ValueError("Baseline and candidate must be different run artifacts")
    baseline, baseline_hash = read_json(project_path(base, baseline_path))
    candidate, candidate_hash = read_json(project_path(base, candidate_path))
    before = validate_run(base, baseline, proposal, "baseline")
    after = validate_run(base, candidate, proposal, "candidate")
    if set(before["evidence"]) & set(after["evidence"]):
        raise ValueError("Baseline and candidate must keep separate evidence artifacts")
    if baseline["run_id"] == candidate["run_id"]:
        raise ValueError("Baseline and candidate run_id must differ")
    for field in MATCHED_FIELDS:
        if baseline[field] != candidate[field]:
            raise ValueError(f"Mismatched run field: {field}")
    regressions = []
    for key, assertions in before["rows"].items():
        for name, passed in assertions.items():
            if passed and not after["rows"][key][name]:
                regressions.append(f"{key[0]} repeat {key[1]} assertion {name}")
    failed_checks = [name for name in proposal["evaluation"]["required_checks"] if not candidate["checks"][name]]
    limits = proposal["evaluation"]
    improvement = limits.get("minimum_improvement", 0.05)
    max_regression = limits.get("maximum_resource_regression", 0.10)
    deltas = {}
    efficiency_gain = False
    resource_regressions = []
    for name in METRICS:
        old, new = before["metrics"][name], after["metrics"][name]
        relative = (new - old) / old if old else (0 if new == 0 else None)
        deltas[name] = {"baseline": old, "candidate": new, "relative_change": relative}
        efficiency_gain |= old > 0 and new < old and (old - new) / old >= improvement
        if (old == 0 and new > 0) or (relative is not None and relative > max_regression):
            resource_regressions.append(name)
    if regressions or failed_checks or resource_regressions:
        verdict = "rejected"
    elif after["passed"] > before["passed"] or efficiency_gain:
        verdict = "eligible"
    else:
        verdict = "inconclusive"
    comparison = {
        "compared_at": timestamp(),
        "verdict": verdict,
        "baseline": {"path": baseline_path, "sha256": baseline_hash, "run_id": baseline["run_id"]},
        "candidate": {"path": candidate_path, "sha256": candidate_hash, "run_id": candidate["run_id"]},
        "passed": {"baseline": before["passed"], "candidate": after["passed"], "total": before["total"]},
        "metrics": deltas,
        "quality_regressions": regressions,
        "failed_checks": failed_checks,
        "resource_regressions": resource_regressions,
        "evidence": {**before["evidence"], **after["evidence"]},
        "claim": "Artifact comparison only; eligibility requires independent review and is not statistical proof.",
    }

    def save(current):
        if current["status"] in ("accepted", "rejected"):
            raise ValueError("Proposal was decided concurrently")
        if current["patch"]["sha256"] != proposal["patch"]["sha256"] or current["evaluation"] != proposal["evaluation"]:
            raise ValueError("Proposal changed during comparison")
        current["comparisons"].append(comparison)
        current["status"] = "evaluated"

    if persist:
        record(base, args.id, save)
    return {"id": args.id, **comparison, "patch_applied": False}


def decide(base, args):
    if not args.reason.strip():
        raise ValueError("A decision reason is required")
    result = {}

    def save(current):
        if current["status"] in ("accepted", "rejected"):
            raise ValueError("Decided proposals are immutable")
        if args.decision == "accept":
            if not current["comparisons"]:
                raise ValueError("Acceptance requires an eligible matched comparison")
            if any(item["verdict"] != "eligible" for item in current["comparisons"]):
                raise ValueError("Every recorded comparison must be eligible; a new proposal is required")
            latest = current["comparisons"][-1]
            for variant in ("baseline", "candidate"):
                artifact = latest[variant]
                if digest(project_path(base, artifact["path"]).read_bytes()) != artifact["sha256"]:
                    raise ValueError(f"{variant} run artifact changed after comparison")
            for ref, expected in latest["evidence"].items():
                if digest(project_path(base, ref).read_bytes()) != expected:
                    raise ValueError(f"Evidence changed after comparison: {ref}")
            if digest(current["patch"]["text"].encode("utf-8")) != current["patch"]["sha256"]:
                raise ValueError("Stored patch changed after proposal")
            fresh = compare(base, SimpleNamespace(id=args.id, baseline=latest["baseline"]["path"],
                                                 candidate=latest["candidate"]["path"]),
                            persist=False, proposal=current)
            if fresh["verdict"] != "eligible":
                raise ValueError("Revalidated comparison is no longer eligible")
            if (fresh["baseline"]["sha256"] != latest["baseline"]["sha256"]
                    or fresh["candidate"]["sha256"] != latest["candidate"]["sha256"]
                    or fresh["evidence"] != latest["evidence"]):
                raise ValueError("Evidence changed while acceptance was being validated")
        current["status"] = "accepted" if args.decision == "accept" else "rejected"
        current["decisions"].append({"at": timestamp(), "decision": args.decision, "reason": args.reason})
        verdicts = [{"compared_at": item["compared_at"], "verdict": item["verdict"]} for item in current["comparisons"]]
        result.update({"id": args.id, "status": current["status"], "reason": args.reason, "verdicts": verdicts,
                       "patch_applied": False})

    record(base, args.id, save)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", default=os.environ.get("AGENT_MEMORY_BASE_DIR") or str(Path(__file__).resolve().parent.parent))
    commands = parser.add_subparsers(dest="command", required=True)
    proposal = commands.add_parser("propose", help="Save a concrete diff, hypothesis and fixed evaluation contract")
    for name in ("title", "hypothesis", "target", "patch", "evaluation", "snapshot"):
        proposal.add_argument("--" + name, required=True)
    comparison = commands.add_parser("compare", help="Compare matched, evidence-linked baseline/candidate run artifacts")
    comparison.add_argument("id")
    comparison.add_argument("--baseline", required=True)
    comparison.add_argument("--candidate", required=True)
    decision = commands.add_parser("decide", help="Record a reviewed accept/reject decision; never apply its diff")
    decision.add_argument("id")
    decision.add_argument("--decision", choices=("accept", "reject"), required=True)
    decision.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    base = Path(args.base_dir).resolve()
    try:
        result = {"propose": propose, "compare": compare, "decide": decide}[args.command](base, args)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.command == "compare":
            return {"eligible": 0, "rejected": 1, "inconclusive": 3}[result["verdict"]]
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
