#!/usr/bin/env python3
"""Score EGM pilot runs: pass counts per (case x assertion) per arm and verdicts.

Reads run directories written by run_pilot.py --live (manifest.json plus
runs/**/run.json and raw outputs). Applies the pre-registered tolerance and
verdict rules from spec.json, refusing to score if the contract or its pinned
inputs changed. --emit-gate also writes baseline/candidate artifacts in the
format scripts/improvement.py compare validates. Every metric is
operator-reported, not a model-certified measurement.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pilot_common as pc  # noqa: E402

IMPROVEMENT_VERDICT = {"evolved": "eligible", "parity": "inconclusive", "regressed": "rejected"}
REQUIRED_CHECKS = ("runs_complete", "runs_succeeded", "isolation_verified")
CLAIM = ("Operator-reported pilot artifacts on one host (Claude Code); not statistical proof and not evidence for "
         "Codex, which stays untested. Protocol-suite wins over native measure EGM-flow conformance, not quality.")


class ScoreError(ValueError):
    """Scoring is not allowed or the run directory is malformed."""


def fixture_text(root: Path) -> str:
    parts = []
    for relative in ("outcome/project", "outcome/overlay-oaw"):
        for path in sorted((root / relative).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def outcome_artifacts(run_dir: Path, record: dict, target: str) -> list[str]:
    texts = []
    for name in record.get("workspace_changes", {}).get("copied", []):
        if name == target or name.startswith((".claude/", ".oaw/")):
            continue
        try:
            texts.append((run_dir / "artifacts" / name).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    return texts


def score_run(context: dict, run_dir: Path, record: dict) -> dict:
    failure, texts, inits, subagents = None, [], [], 0
    metrics, metrics_missing = {"tokens": 0, "latency_ms": 0, "cost_usd": 0.0}, False
    for invocation in record.get("invocations", []):
        stdout = run_dir / invocation.get("stdout", "")
        raw = stdout.read_text(encoding="utf-8", errors="replace") if stdout.is_file() else ""
        parsed = pc.parse_output(raw)
        failure = failure or pc.failure(parsed, invocation)
        texts.append(pc.response_text(parsed))
        used = pc.usage(parsed)
        values = (used["tokens"], used["cost_usd"], invocation.get("wall_ms"))
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
            metrics_missing = True
        else:
            metrics["tokens"] += used["tokens"]
            metrics["cost_usd"] += used["cost_usd"]
            metrics["latency_ms"] += invocation["wall_ms"]
        summary = pc.init_summary(parsed)
        if summary:
            inits.append(summary)
        subagents += pc.subagent_count(parsed)
    expected_invocations = len(context["scenarios"][record["case_id"]]["turns"]) if record["suite"] == "protocol" else 1
    if len(texts) != expected_invocations and failure is None:
        failure = "missing turns"
    case_id = record["case_id"]
    if record["suite"] == "protocol":
        scenario = context["scenarios"][case_id]
        results = {}
        for index, turn in enumerate(scenario["turns"]):
            text = texts[index] if index < len(texts) else ""
            for assertion in turn["assertions"]:
                results[f"{case_id}#{assertion['id']}"] = failure is None and pc.assertion_passes(assertion, text)
        corpus = "\n".join(f"--- turn {index + 1} ---\n{text}" for index, text in enumerate(texts))
    else:
        target = context["defects"]["target"]
        corpus = pc.strip_echo("\n".join(texts + outcome_artifacts(run_dir, record, target)), context["fixture_text"])
        results = {f"{case_id}#{defect['id']}": failure is None and pc.defect_passes(defect, corpus)
                   for defect in context["defects"]["defects"]}
    return {"key": record["key"], "suite": record["suite"], "arm": record["arm"], "case_id": case_id,
            "repeat": record["repeat"], "failure": failure, "assertions": results,
            "metrics": None if metrics_missing else metrics, "subagents": subagents, "inits": inits, "corpus": corpus,
            "invocations": len(texts), "expected_invocations": expected_invocations}


def expected_keys(context: dict, suite: str) -> dict:
    """{case_id: [assertion keys]} for a suite."""
    if suite == "protocol":
        return {case: pc.assertion_keys(scenario) for case, scenario in context["scenarios"].items()}
    ids = [defect["id"] for defect in context["defects"]["defects"]]
    return {case["case_id"]: [f"{case['case_id']}#{name}" for name in ids] for case in context["spec"]["suites"]["outcome"]["cases"]}


def aggregate(context: dict, scored: list[dict], suite: str, arm: str, repeats: int) -> dict:
    keys = expected_keys(context, suite)
    runs = [run for run in scored if run["suite"] == suite and run["arm"] == arm]
    counts = {key: [0, 0] for case_keys in keys.values() for key in case_keys}
    for run in runs:
        for key, passed in run["assertions"].items():
            counts[key][0] += int(passed)
            counts[key][1] += 1
    expected = {(case, repeat) for case in keys for repeat in range(1, repeats + 1)}
    seen = [(run["case_id"], run["repeat"]) for run in runs]
    metrics = None
    if runs and all(run["metrics"] is not None for run in runs):
        metrics = {name: sum(run["metrics"][name] for run in runs) for name in pc.METRICS}
        metrics["cost_usd"] = round(metrics["cost_usd"], 6)
    return {"arm": arm, "repeats": repeats, "runs": len(runs), "counts": counts,
            "checks": {"runs_complete": set(seen) == expected and len(seen) == len(expected),
                       "runs_succeeded": bool(runs) and all(run["failure"] is None for run in runs)},
            "metrics": metrics, "failures": sum(run["failure"] is not None for run in runs),
            "subagents": sum(run["subagents"] for run in runs), "inits": [i for run in runs for i in run["inits"]],
            "manifests": sorted({run["manifest"] for run in runs}),
            "expected_inits": sum(run["expected_invocations"] for run in runs)}


def isolation(spec: dict, groups: list[dict]) -> dict:
    """Required check isolation_verified for each arm in one comparison."""
    shared = {tuple(i["other_plugins"]) for group in groups for i in group["inits"] if i["other_plugins"] is not None}
    models = {i["model"] for group in groups for i in group["inits"]}
    def native(names):
        return tuple(name for name in (names or [])
                     if not name.startswith("egm:") and name != "oaw-evidence" and not name.endswith(":oaw-evidence"))
    signatures = {(native(i.get("skills")), native(i.get("commands")), tuple(i.get("tools") or []))
                  for group in groups for i in group["inits"]}
    banned = set(spec["invocation"].get("disallowed_tools", [])) - {"mcp__*"}
    result = {}
    for group in groups:
        arm = spec["arms"][group["arm"]]
        inits = group["inits"]
        ok = (bool(inits) and len(inits) == group["expected_inits"]
              and len(shared) == 1 and len(models) == 1 and all(isinstance(m, str) and m.strip() for m in models)
              and len(signatures) == 1 and all(
            i["plugins"] is not None and i["mcp_servers"] is not None and not i["mcp_servers"]
            and i.get("skills") is not None and i.get("commands") is not None and i.get("tools") is not None
            and not (set(i["tools"]) & banned)
            and i["egm_loaded"] == arm["egm_plugin"] and i["oaw_loaded"] == bool(arm["oaw"]) for i in inits))
        result[group["arm"]] = ok
    return result


def judge(baseline: dict, candidate: dict, *, tolerance: int, rules: dict) -> dict:
    """Pre-registered verdict for candidate vs baseline from pass counts, checks and metrics."""
    invalid = []
    if set(baseline["counts"]) != set(candidate["counts"]):
        invalid.append("assertion sets differ")
    if baseline["repeats"] != candidate["repeats"]:
        invalid.append("planned repeats differ")
    failed_baseline = [name for name, ok in baseline["checks"].items() if not ok]
    if failed_baseline:
        invalid.append("baseline failed required checks: " + ", ".join(failed_baseline))
    if baseline["metrics"] is None or candidate["metrics"] is None:
        invalid.append("resource metrics are missing for some run")
    if invalid:
        return {"verdict": "invalid", "reasons": invalid, "tolerance": tolerance}
    floor = rules.get("minimum_baseline_assertion_rate", 0)
    if any(not n or passed / n < floor for passed, n in baseline["counts"].values()):
        return {"verdict": "invalid", "reasons": ["baseline below pre-registered assertion floor"], "tolerance": tolerance}
    regressions = [f"{key}: {candidate['counts'][key][0]} vs {passes}" for key, (passes, _) in sorted(baseline["counts"].items())
                   if candidate["counts"][key][0] < passes - tolerance]
    total_baseline = sum(passes for passes, _ in baseline["counts"].values())
    total_candidate = sum(passes for passes, _ in candidate["counts"].values())
    if total_candidate < total_baseline:
        regressions.append(f"total passes: {total_candidate} vs {total_baseline}")
    failed_checks = [name for name, ok in candidate["checks"].items() if not ok]
    deltas, resource_regressions, efficiency = {}, [], []
    for name in pc.METRICS:
        old, new = baseline["metrics"][name], candidate["metrics"][name]
        relative = (new - old) / old if old else (0 if new == 0 else None)
        deltas[name] = {"baseline": old, "candidate": new, "relative_change": relative}
        if (old == 0 and new > 0) or (relative is not None and relative > rules["maximum_resource_regression"]):
            resource_regressions.append(name)
        if old > 0 and new < old and (old - new) / old >= rules["minimum_improvement"]:
            efficiency.append(name)
    if regressions or failed_checks or resource_regressions:
        verdict = "regressed"
    elif total_candidate > total_baseline or efficiency:
        verdict = "evolved"
    else:
        verdict = "parity"
    return {"verdict": verdict, "improvement_py_equivalent": IMPROVEMENT_VERDICT[verdict], "tolerance": tolerance,
            "passes": {"baseline": total_baseline, "candidate": total_candidate,
                       "possible": sum(n for _, n in baseline["counts"].values())},
            "regressions": regressions, "failed_checks": failed_checks,
            "resource_regressions": resource_regressions, "efficiency_gain": efficiency, "metrics": deltas,
            "metrics_label": "operator-reported"}


def load_runs(run_dirs, recorded: str) -> tuple[list, dict]:
    runs, manifests = [], {}
    for directory in run_dirs:
        directory = Path(directory)
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            raise ScoreError(f"{directory} has no manifest.json")
        manifest = pc.load_json(manifest_path)
        if manifest.get("spec_sha256") != recorded:
            raise ScoreError(f"{directory} was run under spec {manifest.get('spec_sha256')}, not the current {recorded}")
        manifests[str(directory)] = manifest
        for path in sorted((directory / "runs").rglob("run.json")):
            runs.append((str(directory), path.parent, pc.load_json(path)))
    return runs, manifests


def snapshot_label(manifest: dict) -> str:
    head = (manifest.get("oaw") or {}).get("head") or "unknown"
    dirty = "+dirty" if (manifest.get("oaw") or {}).get("dirty") else ""
    egm = (manifest.get("egm") or {}).get("commit", "")[:7]
    return f"oaw@{head[:12]}{dirty} egm@{egm} spec@{manifest['spec_sha256'][:12]}"


def emit_gate(out: Path, suite: str, base: dict, cand: dict, scored: list[dict], manifest: dict, verdict: dict,
              rules: dict) -> Path:
    """Write improvement.py-compatible artifacts for one comparison (rows passes-first per assertion)."""
    directory = out / f"{suite}-{cand['arm']}-vs-{base['arm']}"
    directory.mkdir(parents=True, exist_ok=False)
    keys = sorted(base["counts"])
    evaluation = {"schema_version": 1, "id": f"oaw-egm-pilot-{suite}-{cand['arm']}-vs-{base['arm']}",
                  "cases": keys, "repeats": base["repeats"], "assertions": ["passed"],
                  "required_checks": list(REQUIRED_CHECKS),
                  "minimum_improvement": rules["minimum_improvement"],
                  "maximum_resource_regression": rules["maximum_resource_regression"]}
    (directory / "evaluation.json").write_text(json.dumps(evaluation, indent=2) + "\n", encoding="utf-8")
    (directory / "arm.txt").write_text(f"{base['arm']}\n", encoding="utf-8", newline="\n")
    diff = (f"diff --git a/arm.txt b/arm.txt\n--- a/arm.txt\n+++ b/arm.txt\n@@ -1 +1 @@\n"
            f"-{base['arm']}\n+{cand['arm']}\n").encode("utf-8")
    (directory / "arm.diff").write_bytes(diff)
    snapshot = snapshot_label(manifest)
    (directory / "snapshot.txt").write_text(snapshot + "\n", encoding="utf-8")
    for variant, group in (("baseline", base), ("candidate", cand)):
        runs = [run for run in scored if run["suite"] == suite and run["arm"] == group["arm"]]
        evidence = {}
        for run in runs:
            name = f"evidence/{variant}/{pc.sha256(run['key'].encode())[:16]}.txt"
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            header = f"run {run['key']}\nfailure: {run['failure'] or 'none'}\n\n"
            path.write_text(header + run["corpus"], encoding="utf-8")
            evidence[run["key"]] = name
        missing = f"evidence/{variant}/missing-run.txt"
        rows = []
        for key in keys:
            case = key.split("#", 1)[0]
            ordered = sorted((run for run in runs if run["case_id"] == case),
                             key=lambda run: (not run["assertions"][key], run["repeat"]))
            for position, run in enumerate(ordered, 1):
                counted = next(iter(run["assertions"])) == key  # each run's metrics are counted once
                rows.append({"case_id": key, "repeat": position, "source_run": run["key"],
                             "assertions": {"passed": run["assertions"][key]},
                             "tokens": int(run["metrics"]["tokens"]) if counted else 0,
                             "latency_ms": run["metrics"]["latency_ms"] if counted else 0,
                             "cost_usd": run["metrics"]["cost_usd"] if counted else 0,
                             "evidence": [evidence[run["key"]]]})
            for position in range(len(ordered) + 1, group["repeats"] + 1):
                (directory / missing).parent.mkdir(parents=True, exist_ok=True)
                (directory / missing).write_text("planned run has no record; counted as failed\n", encoding="utf-8")
                rows.append({"case_id": key, "repeat": position, "source_run": None, "assertions": {"passed": False},
                             "tokens": 0, "latency_ms": 0, "cost_usd": 0, "evidence": [missing]})
        artifact = {"schema_version": 1, "run_id": f"oaw-egm-pilot-{suite}-{group['arm']}-{manifest['spec_sha256'][:12]}",
                    "variant": variant, "evaluation_id": evaluation["id"], "base_snapshot": snapshot,
                    "model": manifest["model"], "effort": manifest["effort"], "host": manifest["host"]["name"],
                    "host_version": manifest["host"]["version"], "environment": manifest["environment"],
                    "patch_sha256": pc.sha256(diff) if variant == "candidate" else None,
                    "checks": dict(group["checks"]), "cases": rows, "arm": group["arm"],
                    "metrics_label": "operator-reported", "pilot_verdict": verdict["verdict"]}
        (directory / f"{variant}.json").write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return directory


def score(root: Path, run_dirs, *, tolerance_mode: str | None = None, gate_dir: Path | None = None) -> dict:
    root = Path(root)
    problems = pc.spec_problems(root)
    if problems:
        raise ScoreError("pre-registered contract changed: " + "; ".join(problems))
    spec = pc.load_json(root / pc.SPEC_FILE)
    recorded = pc.recorded_spec_digest(root)
    context = {"spec": spec, "scenarios": {s["case_id"]: s for s in pc.load_json(root / pc.SCENARIOS_FILE)["scenarios"]},
               "defects": pc.load_json(root / pc.DEFECTS_FILE), "fixture_text": fixture_text(root)}
    loaded, manifests = load_runs(run_dirs, recorded)
    scored = []
    for manifest_dir, run_dir, record in loaded:
        run = score_run(context, run_dir, record)
        run["manifest"] = manifest_dir
        scored.append(run)
    calibration = any(manifest.get("phase") == "F1" for manifest in manifests.values())
    if tolerance_mode is None:
        tolerance_mode = "live" if all(manifest.get("live") for manifest in manifests.values()) else "deterministic"
    tolerance = spec["tolerance"][tolerance_mode]
    report = {"schema_version": 1, "spec_sha256": recorded, "tolerance_mode": tolerance_mode, "tolerance": tolerance,
              "calibration_only": calibration, "metrics_label": "operator-reported", "claim": CLAIM, "suites": {},
              "gate": []}
    rules = spec["resources"]
    for suite in ("protocol", "outcome"):
        present = {run["arm"] for run in scored if run["suite"] == suite}
        if not present:
            continue
        repeats = spec["suites"][suite]["repeats"]
        groups = {arm: aggregate(context, scored, suite, arm, repeats[arm]) for arm in pc.ARMS if arm in present}
        section = {"arms": {}, "comparisons": []}
        for item in spec["suites"][suite]["comparisons"]:
            base, cand = groups.get(item["baseline"]), groups.get(item["candidate"])
            if base is None or cand is None:
                section["comparisons"].append({**item, "verdict": "missing-arm"})
                continue
            verified = isolation(spec, [base, cand])
            base = {**base, "checks": {**base["checks"], "isolation_verified": verified[base["arm"]]}}
            cand = {**cand, "checks": {**cand["checks"], "isolation_verified": verified[cand["arm"]]}}
            if calibration or not item["verdict"]:
                rates = {key: {"baseline": base["counts"][key], "candidate": cand["counts"][key]} for key in base["counts"]}
                label = "calibration-only" if calibration else ("screening-only" if suite == "outcome" else "sanity-only")
                if not calibration and (not all(base["checks"].values()) or not all(cand["checks"].values())):
                    label = "invalid"
                section["comparisons"].append({**item, "verdict": label,
                                               "quality_claim": False,
                                               "checks": {"baseline": base["checks"], "candidate": cand["checks"]},
                                               "pass_counts": rates})
                continue
            if len(base["manifests"]) != 1 or base["manifests"] != cand["manifests"]:
                result = {"verdict": "invalid", "reasons": ["arms come from different run manifests"]}
            else:
                result = judge(base, cand, tolerance=tolerance,
                               rules={**rules, "minimum_baseline_assertion_rate": spec["suites"][suite].get("minimum_baseline_assertion_rate", 0)})
            section["comparisons"].append({**item, **result})
            if gate_dir is not None and result["verdict"] != "invalid" and base["repeats"] >= 3:
                manifest = manifests[base["manifests"][0]]
                report["gate"].append(str(emit_gate(Path(gate_dir), suite, base, cand, scored, manifest, result, rules)))
        for arm, group in groups.items():
            section["arms"][arm] = {name: group[name] for name in ("repeats", "runs", "counts", "checks", "metrics",
                                                                   "failures", "subagents")}
            section["arms"][arm]["checks"] = {**group["checks"], "isolation_verified": isolation(spec, list(groups.values()))[arm]}
        report["suites"][suite] = section
    return report


def main(argv=None, root: Path | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", action="append", required=True, help="a phase directory from run_pilot.py (repeatable)")
    parser.add_argument("--tolerance", choices=("live", "deterministic"), help="default: live for live manifests")
    parser.add_argument("--emit-gate", metavar="DIR", help="write improvement.py baseline/candidate artifacts here")
    parser.add_argument("--out", help="also write the JSON report to this file")
    args = parser.parse_args(argv)
    try:
        report = score(Path(root or HERE), args.runs, tolerance_mode=args.tolerance,
                       gate_dir=Path(args.emit_gate) if args.emit_gate else None)
    except (ScoreError, OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
