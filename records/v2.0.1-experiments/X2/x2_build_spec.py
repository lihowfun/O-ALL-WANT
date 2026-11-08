"""Build the frozen X2 case set (PREREG.md "核實" and "凍結"): apply the two-family verification rules, copy the cases,
and write spec.json with every rubric, the case digests and the order, descriptive and calibration lists.

Rules, per new case, using each family's latest verdict (later verify files override earlier ones):
- a planted defect stays only if both families judged it real; a trap stays only if both judged it correct;
- a clean case with any other defect reported by either family is dropped;
- a defect case with another reported defect stops the build (revise and verify again first);
- a calibration case revised twice may keep another reported defect when named in --accept-extra: calibration
  measures run-to-run noise only, and an unplanted defect can only raise that noise (floors are never lowered).

    python3 x2_build_spec.py --batch CASES_A=verify-a.jsonl,verify-b.jsonl,verify-r2.jsonl --batch CASES_B=v2.jsonl \
        --bank BANK --bank-spec egm-local/spec.json --categories categories.json,categories-2.json \
        --order order.json --out FINAL
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from x2_run import tree_digest  # noqa: E402

DESCRIPTIVE = ["events", "clean"]


def latest_verdicts(paths):
    latest = {}
    for path in paths:
        for line in open(path, encoding="utf-8"):
            row = json.loads(line)
            latest[(row["id"], row["family"])] = row["verdict"]
    return latest


def verified_after_last_change(cases_dir, cid):
    """The ledger must show both families' last verify after the case's last author or revise step."""
    steps = [json.loads(l) for l in open(os.path.join(cases_dir, "ledger.jsonl"), encoding="utf-8")]
    changed = max((n for n, s in enumerate(steps) if s["id"] == cid and s["step"] in ("author", "revise")), default=None)
    if changed is None:
        return False
    return all(any(s["id"] == cid and s["step"] == "verify" and s["family"] == f for s in steps[changed + 1:])
               for f in ("opus", "codex"))


def complete_verdict(verdict, doc):
    """Every planted defect has a boolean real, every trap a boolean correct, other_defects is a list."""
    if not isinstance(verdict, dict) or "unparsed" in verdict or not isinstance(verdict.get("other_defects"), list):
        return False
    defects = [d for d in verdict.get("defects") or [] if isinstance(d, dict)]
    traps = [t for t in verdict.get("traps") or [] if isinstance(t, dict)]
    if len({d.get("id") for d in defects}) != len(defects) or len({t.get("id") for t in traps}) != len(traps):
        return False  # one id judged twice, possibly both ways
    real = {d.get("id"): d.get("real") for d in defects}
    right = {t.get("id"): t.get("correct") for t in traps}
    return (all(isinstance(real.get(d["id"]), bool) for d in doc["defects"])
            and all(isinstance(right.get(t["id"]), bool) for t in doc["traps"]))


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--batch", action="append", required=True, help="CASES_DIR=verify1.jsonl,verify2.jsonl")
    p.add_argument("--bank", required=True)
    p.add_argument("--bank-spec", required=True)
    p.add_argument("--categories", required=True)
    p.add_argument("--order", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--accept-extra", default="", help="calibration cases allowed to keep reported extra defects")
    a = p.parse_args(argv)
    planned = {}
    for path in a.categories.split(","):
        for case in json.load(open(path, encoding="utf-8"))["cases"]:
            planned[case["id"]] = dict(case, role=case.get("role", "primary"))
    order = json.load(open(a.order, encoding="utf-8"))
    bank = json.load(open(a.bank_spec, encoding="utf-8"))
    os.makedirs(os.path.join(a.out, "cases"), exist_ok=True)
    rubric, digests, report, dropped = {}, {}, {}, []
    seen_ids = set()
    for batch in a.batch:
        cases_dir, files = batch.split("=", 1)
        verdicts = latest_verdicts(files.split(","))
        for name in sorted(os.listdir(os.path.join(cases_dir, "authored"))):
            if not name.endswith(".json") or name.startswith("authored-pre"):
                continue
            cid = name[:-5]
            doc = json.load(open(os.path.join(cases_dir, "authored", name), encoding="utf-8"))
            missing = [f for f in ("opus", "codex") if not complete_verdict(verdicts.get((cid, f)), doc)]
            if missing:
                raise SystemExit(f"{cid}: no complete verdict from {missing}")
            if not verified_after_last_change(cases_dir, cid):
                raise SystemExit(f"{cid}: the last verification predates the last author or revise step")
            seen_ids.add(cid)
            real = {f: {d["id"]: d.get("real") for d in verdicts[(cid, f)].get("defects", [])} for f in ("opus", "codex")}
            right = {f: {t["id"]: t.get("correct") for t in verdicts[(cid, f)].get("traps", [])} for f in ("opus", "codex")}
            other = [dict(o, family=f) for f in ("opus", "codex") for o in verdicts[(cid, f)].get("other_defects", [])]
            wrong_traps = sorted({t["id"] for t in doc["traps"] for f in ("opus", "codex") if right[f].get(t["id"]) is False})
            if wrong_traps and cid not in set(filter(None, a.accept_extra.split(","))):  # a trap judged a real defect means the case holds an unplanted defect: revise first
                raise SystemExit(f"{cid}: traps {wrong_traps} judged incorrect; revise and verify again")
            kept_defects = [d for d in doc["defects"] if all(real[f].get(d["id"]) is True for f in ("opus", "codex"))]
            kept_traps = [t for t in doc["traps"] if all(right[f].get(t["id"]) is True for f in ("opus", "codex"))]
            entry = {"kind": planned[cid]["kind"], "author": planned[cid]["author"], "role": planned[cid]["role"],
                     "planted": [d["id"] for d in doc["defects"]], "kept_defects": [d["id"] for d in kept_defects],
                     "traps": [t["id"] for t in doc["traps"]], "kept_traps": [t["id"] for t in kept_traps],
                     "other_defects": other}
            report[cid] = entry
            if other and planned[cid]["kind"] == "clean":
                dropped.append(cid)
                entry["dropped"] = "clean case with another reported defect"
                continue
            accepted = cid in set(filter(None, a.accept_extra.split(",")))
            if accepted and planned[cid]["role"] != "calibration":
                raise SystemExit(f"{cid}: --accept-extra is for calibration cases only")
            if other and not accepted:
                raise SystemExit(f"{cid}: other defects still reported ({len(other)}); revise and verify again")
            if other:
                entry["accepted_extra"] = "calibration case revised twice; extra defects recorded, not in the rubric"
            if planned[cid]["kind"] == "defect" and not kept_defects:
                dropped.append(cid)
                entry["dropped"] = "no planted defect confirmed by both families"
                continue
            groups = {"critical": [], "major": [], "hard_negatives": [t["rubric"] for t in kept_traps]}
            for d in sorted(kept_defects, key=lambda d: d["id"]):
                groups[d["severity"]].append(d["rubric"])
            rubric[cid] = groups
            shutil.rmtree(os.path.join(a.out, "cases", cid), ignore_errors=True)
            shutil.copytree(os.path.join(cases_dir, "cases", cid), os.path.join(a.out, "cases", cid))
    unauthored = sorted(set(planned) - seen_ids)
    if unauthored:
        raise SystemExit(f"planned cases without an authored and verified version: {unauthored}")
    for cid in DESCRIPTIVE:
        rubric[cid] = bank["rubric"][cid]
        shutil.rmtree(os.path.join(a.out, "cases", cid), ignore_errors=True)
        shutil.copytree(os.path.join(a.bank, "cases", cid), os.path.join(a.out, "cases", cid))
        report[cid] = {"kind": "defect" if bank["rubric"][cid].get("critical") or bank["rubric"][cid].get("major")
                       else "clean", "role": "descriptive", "source": "evals/egm-local (frozen 2026-10-29)"}
    for cid in os.listdir(os.path.join(a.out, "cases")):
        digests[cid] = tree_digest(os.path.join(a.out, "cases", cid))
    calibration = sorted(c for c, e in report.items() if e.get("role") == "calibration" and c in rubric)
    planned_calibration = sorted(c for c, e in planned.items() if e["role"] == "calibration")
    if calibration != planned_calibration:
        raise SystemExit(f"calibration cases {calibration} differ from the plan {planned_calibration}; author a "
                         "replacement before freezing")
    run_order = [c for c in order if c in rubric]
    lost = [c for c in order if c not in rubric]
    spec = {"frozen": "X2 confirmatory set (PREREG.md); built by x2_build_spec.py",
            "order": run_order, "descriptive": DESCRIPTIVE, "calibration": calibration,
            "planned_primary": sorted(c for c, e in planned.items() if e["role"] == "primary"),
            "planned_calibration": planned_calibration,
            "rubric": rubric, "case_digests": digests,
            "inputs": {name: sha(os.path.join(HERE, name)) for name in
                       ("categories.json", "categories-2.json", "checklist_R.md", "x2_case_tools.py")},
            "dropped": dropped, "dropped_from_order": lost}
    json.dump(spec, open(os.path.join(a.out, "spec.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(report, open(os.path.join(a.out, "verification.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    primary = [c for c in run_order if c not in DESCRIPTIVE]
    defect = [c for c in primary if rubric[c]["critical"] or rubric[c]["major"]]
    print(f"primary {len(primary)} ({len(defect)} defect, {len(primary) - len(defect)} clean); descriptive "
          f"{DESCRIPTIVE}; calibration {calibration}; dropped {dropped}; planted defects kept "
          f"{sum(len(rubric[c]['critical']) + len(rubric[c]['major']) for c in defect)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
