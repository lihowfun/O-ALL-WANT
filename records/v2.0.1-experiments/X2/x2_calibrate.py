"""X2 floors from calibration (D36, PREREG.md): run-to-run noise of the native arm on each host, measured on the
three calibration cases (N, 3 runs each, graded by both families), never used in the primary analysis.

For each host cell and grader family: the pooled within-case SD of the detection rate and of the unsupported-claim
count. The floor used by x2_judge.py is the larger of that measured value and the borrowed 2026-11-08 value
(floor.json): calibration can raise a floor, never lower it.

    python3 x2_calibrate.py --eval-stats eval_stats.py --cases CASES --borrowed floor.json \
        --rows cal-claude/rows.jsonl,cal-codex/rows.jsonl --grades cal-grades-opus.jsonl,cal-grades-codex.jsonl \
        --out floor-final.json
Every (host, grader family, case, run 1-3) must have exactly one grade with a matching run row, or nothing is written.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--eval-stats", required=True)
    p.add_argument("--cases", required=True)
    p.add_argument("--borrowed", required=True)
    p.add_argument("--rows", required=True)
    p.add_argument("--grades", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    spec = importlib.util.spec_from_file_location("eval_stats", a.eval_stats)
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    spec_path = os.path.join(a.cases, "spec.json")
    cases = json.load(open(spec_path, encoding="utf-8"))
    spec_sha = hashlib.sha256(open(spec_path, "rb").read()).hexdigest()
    borrowed = json.load(open(a.borrowed, encoding="utf-8"))
    calibration = cases["calibration"]
    if calibration != cases.get("planned_calibration") or len(calibration) < 3:
        raise SystemExit(f"calibration cases {calibration} differ from the frozen plan; the floor is unresolved")
    reports, versions = {}, {"runner": set(), "grader": {"opus": set(), "codex": set()}}
    wanted = {(cell, cid, rep) for cell in ("claude", "codex") for cid in calibration for rep in (1, 2, 3)}
    runs = set()
    for path in a.rows.split(","):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            key = (r["cell"], r["id"], r.get("rep", 1))
            if r["arm"] != "N" or key not in wanted or key in runs:
                raise SystemExit(f"unexpected or duplicate calibration row {key} ({r['arm']})")
            if r.get("spec_sha256") != spec_sha or r.get("prepared", {}).get("case_digest") != cases["case_digests"][r["id"]]:
                raise SystemExit(f"calibration row {key} was run against another spec or other case files")
            runs.add(key)
            reports[key] = hashlib.sha256(json.dumps(r.get("report"), sort_keys=True).encode()).hexdigest()
            versions["runner"].add(r.get("runner_sha256"))
    if runs != wanted:
        raise SystemExit(f"calibration rows missing: {sorted(wanted - runs)}; the floor is unresolved")
    cells, seen = {}, set()
    for path in a.grades.split(","):
        for line in open(path, encoding="utf-8"):
            g = json.loads(line)
            if g["family"] not in ("opus", "codex"):
                continue
            key = (g["family"], g["cell"], g["id"], g.get("rep", 1))
            if g["arm"] != "N" or key[1:] not in wanted or key in seen:
                raise SystemExit(f"unexpected or duplicate calibration grade {key}")
            if g.get("spec_sha256") != spec_sha or g.get("report_sha256") != reports.get(key[1:]):
                raise SystemExit(f"calibration grade {key} used another spec or graded another report")
            versions["grader"][g["family"]].add(g.get("grader_sha256"))
            seen.add(key)
            fam = cells.setdefault(g["cell"], {}).setdefault(g["family"], {"det": {}, "unsup": {}})
            fam["det"].setdefault(g["id"], []).append(len(g["detected"]) / g["planted"])
            fam["unsup"].setdefault(g["id"], []).append(g["unsupported"])
    for name, values in (("runner", versions["runner"]), ("opus grader", versions["grader"]["opus"]),
                         ("codex grader", versions["grader"]["codex"])):
        if len(values) != 1 or None in values:
            raise SystemExit(f"calibration {name} versions are missing or mixed: {values}")
    missing = {(f,) + k for f in ("opus", "codex") for k in wanted} - seen
    if missing:
        raise SystemExit(f"calibration grades missing: {sorted(missing)[:6]}; the floor is unresolved")
    result = {"rule": "floor = max(measured pooled within-case SD of N on the calibration cases, borrowed value)",
              "calibration_cases": calibration, "spec_sha256": spec_sha,
              "inputs": {path: hashlib.sha256(open(path, "rb").read()).hexdigest()
                         for path in a.rows.split(",") + a.grades.split(",")}}
    for cell in ("claude", "codex"):
        for fam in ("opus", "codex"):
            data = cells[cell][fam]
            runs = sum(len(v) for v in data["det"].values())
            measured = {"detection": S.pooled_within_sd(data["det"]), "unsupported": S.pooled_within_sd(data["unsup"])}
            result.setdefault(cell, {})[fam] = {
                metric: max(measured[metric], borrowed[fam][metric]) for metric in ("detection", "unsupported")}
            result[cell][fam].update({"measured": measured, "borrowed": {m: borrowed[fam][m] for m in measured},
                                      "runs": runs})
    json.dump(result, open(a.out, "w", encoding="utf-8"), indent=1)
    print(json.dumps({c: {f: {m: round(result[c][f][m], 4) for m in ("detection", "unsupported")}
                          for f in ("opus", "codex")} for c in ("claude", "codex")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
