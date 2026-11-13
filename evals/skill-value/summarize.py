#!/usr/bin/env python3
"""Offline decision rules registered before outputs. No model calls or guesses."""
import argparse
import json
from pathlib import Path

CONDITIONS = ("EGM", "V2 skill off", "V2 skill on")
FLAGS = ("citations_supported", "before_receiver_provenance", "artifact_semantics_correct")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def grade_rows(answer, expected):
    rows = answer.get("answers", {}).get("reports")
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise ValueError("Incomplete semantic grading population")
    result = {}
    for row in rows:
        if row.get("id") in result or row.get("id") not in expected or any(type(row.get(k)) is not bool for k in FLAGS) or not isinstance(row.get("unsupported_claims"), list):
            raise ValueError("Missing, duplicate or malformed semantic grade")
        result[row["id"]] = row
    return result


def signature(row):
    return tuple(row[k] for k in FLAGS) + (json.dumps(row["unsupported_claims"], sort_keys=True),)


def semantic_grades(out):
    import experiment
    registration = read(out / "grading-registration.json")
    output_hashes = read(out / "semantic-output-hashes.json")
    if output_hashes["grades"] != experiment.tree(out / "grades") or output_hashes["adjudication_jobs_sha256"] != experiment.sha(out / "adjudication-jobs.json"):
        raise ValueError("Semantic grades/adjudication drift")
    if registration["jobs_sha256"] != experiment.sha(out / "grading-jobs.json") or registration["mapping_sha256"] != experiment.sha(out / "grading-map-private.json"):
        raise ValueError("Grading population/mapping drift")
    jobs = read(out / "grading-jobs.json")
    mapping = read(out / "grading-map-private.json")
    result = {}
    for group in sorted({j["group"] for j in jobs}):
        pair = [j for j in jobs if j["group"] == group]
        for job in pair:
            current = {k: v for k, v in experiment.tree(job["workspace"]).items() if not k.startswith("artifacts/")}
            if current != job["input_hashes"] or experiment.sha(Path(job["workspace"]) / "packet.json") != job["packet_sha256"]:
                raise ValueError("Graded source/packet changed")
        expected = [r["id"] for r in read(Path(pair[0]["workspace"]) / "packet.json")["reports"]]
        for entry in read(Path(pair[0]["workspace"]) / "packet.json")["reports"]:
            original = mapping[group + "/" + entry["id"]]["id"]
            if entry["report"] != read(out / "reports" / (original + ".json")):
                raise ValueError("Anonymous report does not match frozen original")
        primary = [grade_rows(read(out / "grades" / (j["id"] + ".json")), expected) for j in pair]
        disagreement = any(signature(primary[0][k]) != signature(primary[1][k]) for k in expected)
        resolved = grade_rows(read(out / "grades" / (group + "-adjudication.json")), expected) if disagreement else primary[0]
        for anon, row in resolved.items():
            ident = mapping[group + "/" + anon]["id"]
            result[ident] = {"pass": all(row[k] for k in FLAGS) and not row["unsupported_claims"], "unsupported_claims": row["unsupported_claims"], "issues": row.get("issues", []), "adjudicated": disagreement}
    return result


def decide(groups):
    """All paired sessions and both families are required, no weighted tradeoff."""
    if any(not g["complete"] for g in groups.values()):
        return "INCONCLUSIVE: incomplete population, usage or semantic audit"
    on = groups["V2 skill on"]
    if on["unsafe"] or on["successes"] != on["planned"]:
        return "BLOCK PROMOTION: focused skill failed an absolute primary endpoint"
    for baseline in ("EGM", "V2 skill off"):
        if any(passed and not on["paired_pass"][key] for key, passed in groups[baseline]["paired_pass"].items()):
            return "REGRESSION: a paired baseline success was lost"
    families = on["families"]
    quality = all(on["families"][family]["successes"] > groups[base]["families"][family]["successes"] for family in families for base in ("EGM", "V2 skill off"))
    if quality:
        return "OBSERVED QUALITY GAIN: exploratory support in both registered families"
    all_pass = all(g["successes"] == g["planned"] for g in groups.values())
    efficient = all(on["families"][family]["tokens"] <= 0.85 * groups[base]["families"][family]["tokens"] for family in families for base in ("EGM", "V2 skill off"))
    if all_pass and efficient:
        return "OBSERVED EFFICIENCY GAIN: quality held, >=15% fewer tokens in each family"
    if groups["V2 skill off"]["successes"] > groups["EGM"]["successes"] and on["paired_pass"] == groups["V2 skill off"]["paired_pass"]:
        return "POSSIBLE HELPER VALUE: no demonstrated increment from focused SKILL text"
    return "NO DEMONSTRATED SKILL GAIN: prefer opt-in; not proof of universal uselessness"


def summarize(out):
    import experiment
    out = Path(out)
    experiment.verify_evidence(out)
    manifest = read(out / "manifest.json")
    try:
        grades = semantic_grades(out)
        grade_error = None
    except (ValueError, KeyError, FileNotFoundError) as exc:
        grades, grade_error = {}, str(exc)
    modules = {}
    details = []
    for module in manifest["protocol"]["modules"]:
        groups = {c: {"planned": 0, "completed": 0, "successes": 0, "unsafe": 0, "complete": True, "fields_correct": 0, "fields_planned": 0, "input": 0, "cached": 0, "output": 0, "tokens": 0, "paired_pass": {}, "families": {}} for c in CONDITIONS}
        for item in [t for t in manifest["trials"] if t["module"] == module]:
            data = read(out / "definitions" / (module + "-" + item["case"] + ".json"))
            stats = groups[item["condition"]]
            family = stats["families"].setdefault(item["case"], {"successes": 0, "tokens": 0})
            for stage in range(1, len(data["prompts"]) + 1):
                ident = item["id"] + f"-s{stage}"
                stats["planned"] += 1
                stats["fields_planned"] += len(data["gold"][stage - 1])
                row_path, check_path = out / "raw" / ident / "result.json", out / "checks" / (ident + ".json")
                row = read(row_path) if row_path.exists() else {"status": "not_started", "usage": None}
                checks = read(check_path) if check_path.exists() else {"fields": {}, "artifacts": {}}
                report_path = out / "reports" / (ident + ".json")
                after = out / "snapshots" / ident / "after"
                if report_path.exists() and after.is_dir():
                    fields = experiment.answer_checks(data, stage, read(report_path))
                    artifacts = experiment.artifact_checks(module, item["case"], data, after, stage)
                    if fields != checks["fields"] or any(checks["artifacts"].get(k) != v for k, v in artifacts.items()):
                        raise ValueError("Stored checks differ from frozen answer/artifacts")
                if row.get("usage") is not None:
                    events = [json.loads(line) for line in (out / "raw" / ident / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.startswith("{")]
                    if row["usage"] != experiment.usage(events):
                        raise ValueError("Usage differs from native event evidence")
                audit = grades.get(ident)
                valid = row["status"] == "complete" and row.get("io_verified") is True
                stats["completed"] += int(valid)
                stats["complete"] &= valid and row.get("usage") is not None and audit is not None
                stats["fields_correct"] += sum(v is True for v in checks["fields"].values())
                passed = valid and bool(checks["fields"]) and all(checks["fields"].values()) and bool(checks["artifacts"]) and all(checks["artifacts"].values()) and audit is not None and audit["pass"]
                stats["successes"] += int(passed)
                family["successes"] += int(passed)
                stats["paired_pass"][item["case"] + f"-r{item['repeat']}-s{stage}"] = passed
                unsafe = audit is not None and bool(audit["unsupported_claims"])
                stats["unsafe"] += int(unsafe)
                if row.get("usage"):
                    u = row["usage"]
                    for field, source in (("input", "input_tokens"), ("cached", "cached_input_tokens"), ("output", "output_tokens")):
                        stats[field] += u[source]
                    total = u["input_tokens"] + u["output_tokens"]
                    stats["tokens"] += total
                    family["tokens"] += total
                details.append({"id": ident, "module": module, "condition": item["condition"], "case": item["case"], "repeat": item["repeat"], "stage": stage, "passed": passed, "checks": checks, "semantic_audit": audit, "status": row["status"]})
        modules[module] = {"groups": groups, "decision": decide(groups)}
    return {"protocol": manifest["protocol"]["id"], "source": manifest["protocol"]["product_commit"], "modules": modules, "semantic_grade_error": grade_error, "details": details, "scope": "Candidate logical usage includes IO and tool context. Graders/setup/failed usage and Python controller scope reported separately; no dollars or universal superiority."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--write", required=True)
    args = parser.parse_args()
    result = summarize(args.out)
    Path(args.write).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v["decision"] for k, v in result["modules"].items()}))
