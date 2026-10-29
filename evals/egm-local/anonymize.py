#!/usr/bin/env python3
"""Export all registered fixture reviews for independent semantic grading.

Never dispatches models. Preserves all findings and uncertainties while removing
execution metadata and normalizing known host workspace paths. The fixed private
map is supplied by the operator and must not be given to graders. Writing into
an existing destination is refused to preserve grading artifacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import prepare


def normalize(value, runs):
    if isinstance(value, str):
        for run in runs:
            workspace = run["workspace"]
            for prefix in (workspace, workspace.replace("\\", "/"), workspace.replace("/", "\\")):
                value = value.replace(prefix + "/", "").replace(prefix + "\\", "")
                value = value.replace(prefix, "project")
        return value
    if isinstance(value, list):
        return [normalize(item, runs) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item, runs) for key, item in value.items()}
    return value


def export(run_dir, output):
    spec, checksum = prepare.verify()
    run_dir, output = Path(run_dir), Path(output)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    mapping = json.loads((run_dir / "blind-map-private.json").read_text(encoding="utf-8-sig"))
    if manifest["spec_sha256"] != checksum:
        raise ValueError("Wrong registration")
    runs = manifest["runs"]
    lookup = {run["id"]: run for run in runs}
    expected = {f"{case}-r{repeat}-{arm}" for case in spec["cases"]
                for repeat in range(1, 4) for arm in spec["arms"]}
    mapped = [trial for entries in mapping.values() for trial in entries.values()]
    if set(lookup) != expected or len(runs) != 27 or set(mapped) != expected or len(mapped) != 27:
        raise ValueError("All 27 unique trials and a complete private mapping are required")
    bundles = {}
    for case in spec["cases"]:
        entries = mapping[case]
        if set(entries) != {f"R{i:02d}" for i in range(1, 10)}:
            raise ValueError("Expected nine anonymous IDs per case")
        reviews = []
        for anonymous_id, trial_id in entries.items():
            run = lookup[trial_id]
            if run["case"] != case:
                raise ValueError("Private map crosses case boundaries")
            prepare.verify_workspace(run)
            report = json.loads(Path(run["report"]).read_text(encoding="utf-8-sig"))
            if report.get("completed") is not True or not isinstance(report.get("findings"), list):
                raise ValueError("Incomplete review: " + trial_id)
            findings = []
            for index, finding in enumerate(report["findings"], 1):
                if not isinstance(finding, dict):
                    raise ValueError("Malformed finding: " + trial_id)
                required = ("location", "claim", "evidence", "rationale", "severity")
                if not all(key in finding for key in required):
                    raise ValueError("Missing finding evidence: " + trial_id)
                findings.append({**normalize(finding, runs), "finding_id": f"F{index:02d}"})
            reviews.append({"review_id": anonymous_id, "completed": True,
                            "findings": findings,
                            "uncertainties": normalize(report.get("uncertainties", []), runs)})
        bundles[case] = {"reviews": reviews}
    if output.exists():
        raise ValueError("Choose a fresh grading destination")
    output.mkdir(parents=True)
    for case, bundle in bundles.items():
        rubric = spec["rubric"][case]
        converted = {"case": case, **rubric}
        for category, prefix in (("critical", "C"), ("major", "M")):
            converted[category] = [{"id": f"{prefix}{i}", "description": item}
                                   for i, item in enumerate(rubric[category], 1)]
        for grader in (1, 2):
            target = output / case / f"grader{grader}"
            target.mkdir(parents=True)
            shutil.copytree(prepare.HERE / "cases" / case, target / "project")
            shutil.copyfile(prepare.HERE / "grade_prompt.md", target / "grade_prompt.md")
            for filename, data in (("rubric.json", converted), ("reviews.json", bundle)):
                (target / filename).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"spec_sha256": checksum, "anonymous_reviews": 27,
            "independent_grading_packets": 6,
            "blinding_limit": "Execution labels removed; style and cited guidance may still reveal treatment. No full double-blind claim."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.run_dir, args.out), indent=2))


if __name__ == "__main__":
    main()
