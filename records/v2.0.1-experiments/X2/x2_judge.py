"""X2 decision (PREREG.md). Statistics through OAW's scripts/eval_stats.py (its bootstrap, quantile and floor rules);
only the confidence level is corrected here for three comparisons per cell (Bonferroni).

Per cell (claude, codex) the arms are N, R, E of that cell and X = the other cell's N on the same case. Per grader
family (opus, codex):
- detection rate on the primary defect cases (detected / planted): superiority over N needs the lower end of the
  one-sided (1 - 0.025/3) interval above 0;
- unsupported claims per report on all primary cases: non-inferiority needs the upper end of the one-sided
  (1 - 0.05/3) interval of (arm - N) below 0.5.
Floors (minimum standard error) come per cell and grader family from floor-final.json (x2_calibrate.py); a comparison
that involves X uses the larger of the two cells' floors.

An arm qualifies when both families establish superiority in detection, both establish non-inferiority in unsupported
claims, no clean-case report has a false alarm both families found, and (E only) at most 2 primary E runs lacked the
full reviewer launches. Among qualified arms the best is the highest mean detection (both families averaged); a tie
at the top that is not equivalent for both families is unresolved. The pool is the best plus every qualified arm
both families judge equivalent to it (compare(arm, best, 0.10)); the pick is the pool member with the lowest median
logical tokens on this cell's own provider; X (another provider) is picked only when it is the whole pool. No
qualified arm: the host keeps N. Sensitivity: the decision is repeated with the superiority floors x1.5 and the
non-inferiority floors at max(1.5 x measured, borrowed) (the borrowed values were measured on repeated native and EGM
reviews, so they already reflect the arms' spread; only the 6-df N measurement gets the extra margin); equivalence keeps
its floors. A different pick there makes the cell unresolved. Full x1.5 non-inferiority results are reported. Any missing row, grade, case or binding mismatch makes the cell unresolved or stops the judge.

    python3 x2_judge.py --eval-stats eval_stats.py --cases CASES --floor floor-final.json --claude-rows A --codex-rows B \
        --grades grades-opus.jsonl,grades-codex.jsonl --out judge.json
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import statistics
import sys
from statistics import NormalDist

ARMS = ("R", "X", "E")          # the comparisons against N in one cell (the Bonferroni family)
SENSITIVITY = 1.5               # every detection floor x1.5: about the 85% upper confidence limit of an SD with 6 df
FAMILIES = ("opus", "codex")


def load_stats(path):
    spec = importlib.util.spec_from_file_location("eval_stats", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corrected(S, food, native, floor_sd, alpha_one_sided):
    """eval_stats' interval (same draws, seed and floor rule) at a corrected one-sided level."""
    diffs = S._per_question(food, native, log_ratio=False)
    values = list(diffs.values())
    point = statistics.fmean(values)
    boot = S._bootstrap(values, S.DRAWS, S.SEED)
    se_boot = statistics.pstdev(boot)
    floor_se = floor_sd * math.sqrt(2 / len(values)) if floor_sd else 0.0
    if floor_se > se_boot:
        z = NormalDist().inv_cdf(1 - alpha_one_sided)
        lo, hi = point - z * floor_se, point + z * floor_se
    else:
        lo, hi = S._quantile(boot, alpha_one_sided), S._quantile(boot, 1 - alpha_one_sided)
    return {"point": point, "lo": lo, "hi": hi, "se": max(floor_se, se_boot), "floor_applied": floor_se > se_boot}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--eval-stats", required=True)
    p.add_argument("--cases", required=True)
    p.add_argument("--floor", required=True)
    p.add_argument("--claude-rows", required=True)
    p.add_argument("--codex-rows", required=True)
    p.add_argument("--grades", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    S = load_stats(a.eval_stats)
    spec_path = os.path.join(a.cases, "spec.json")
    cases = json.load(open(spec_path, encoding="utf-8"))
    spec_sha = hashlib.sha256(open(spec_path, "rb").read()).hexdigest()
    floor = json.load(open(a.floor, encoding="utf-8"))
    problems = []

    ids = [c for c in cases["order"] if c not in cases.get("descriptive", [])]
    if "planned_primary" not in cases:
        problems.append("spec.json has no planned_primary list")
    if floor.get("spec_sha256") != spec_sha:
        problems.append("floor-final.json was calibrated against another spec")
    expected = set(cases.get("planned_primary", [])) - set(cases.get("dropped", []))
    if set(ids) != expected:
        problems.append(f"primary cases {sorted(set(ids) ^ expected)} differ from the frozen plan")
    defect = [c for c in ids if cases["rubric"][c].get("critical") or cases["rubric"][c].get("major")]
    clean = [c for c in ids if c not in defect]

    rows = {}
    for cell, path in (("claude", a.claude_rows), ("codex", a.codex_rows)):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            key = (cell, r["arm"], r["id"])
            if key in rows:
                problems.append(f"duplicate row {key}")
            rows[key] = r
            if r.get("spec_sha256") != spec_sha:
                problems.append(f"row {key} was run against another spec")
            if r.get("prepared", {}).get("case_digest") != cases["case_digests"].get(r["id"]):
                problems.append(f"row {key} case files differ from the frozen digest")
    for field in ("runner_sha256", "oaw_src_sha256"):
        versions = {r.get(field) for r in rows.values()}
        if len(versions) != 1 or None in versions:
            problems.append(f"rows mix {field} values: {len(versions)}")
    grades = {}
    for path in a.grades.split(","):
        for line in open(path, encoding="utf-8"):
            g = json.loads(line)
            if g["family"] not in FAMILIES:
                continue  # descriptive graders never enter the decision
            key = (g["family"], g["cell"], g["arm"], g["id"])
            if key in grades:
                problems.append(f"duplicate grade {key}")
            grades[key] = g
            row = rows.get((g["cell"], g["arm"], g["id"]))
            if row is None:
                problems.append(f"grade {key} has no row")
            elif g.get("report_sha256") != hashlib.sha256(json.dumps(row.get("report"), sort_keys=True).encode()).hexdigest():
                problems.append(f"grade {key} graded another report")
            if g.get("spec_sha256") != spec_sha:
                problems.append(f"grade {key} used another spec")
    for fam in FAMILIES:
        versions = {g.get("grader_sha256") for k, g in grades.items() if k[0] == fam}
        if len(versions) != 1 or None in versions:
            problems.append(f"{fam} grades mix grader versions")
    if problems:
        json.dump({"status": "refused", "problems": problems}, open(a.out, "w", encoding="utf-8"), indent=1)
        print("refused:", *problems[:10], sep="\n  ")
        return 2

    other = {"claude": "codex", "codex": "claude"}

    def source(cell, arm):
        return (other[cell], "N") if arm == "X" else (cell, arm)

    def complete(cell, arm):
        c, r = source(cell, arm)
        return all((c, r, i) in rows for i in ids) and all((fam, c, r, i) in grades for fam in FAMILIES for i in ids)

    def metric(fam, cell, arm, name):
        c, r = source(cell, arm)
        out = {}
        for i in (defect if name in ("det", "seen") else ids):
            g = grades[(fam, c, r, i)]
            if name == "det":
                out[i] = [len(g["detected"]) / g["planted"]]
            elif name == "seen":
                out[i] = [(len(g["detected"]) + len(g["mentioned_only"])) / g["planted"]]
            else:
                out[i] = [g["unsupported"]]
        return out

    def fsd(cell, arms, fam, name, mode):
        """primary floors; "sup" = x1.5 (superiority rerun); "ni" = max(1.5 x measured, borrowed)."""
        cells = {cell} | ({other[cell]} if "X" in arms else set())
        if mode == "ni":
            return max(max(SENSITIVITY * floor[c][fam]["measured"][name], floor[c][fam]["borrowed"][name]) for c in cells)
        return (SENSITIVITY if mode == "sup" else 1.0) * max(floor[c][fam][name] for c in cells)

    def tokens(cell, arm, key="tokens_total"):
        c, r = source(cell, arm)
        return [rows[(c, r, i)][key] for i in ids]

    def decide(cell, sensitive):
        arms = [x for x in ("N", "R", "X", "E") if complete(cell, x)]
        doc = {"sensitivity_run": sensitive, "arms": {}, "incomplete": [x for x in ("N", "R", "X", "E") if x not in arms]}
        if doc["incomplete"]:
            doc["pick"], doc["reason"] = None, f"unresolved: incomplete arms {doc['incomplete']}"
            return doc
        doc["e_noncompliant"] = [i for i in ids if rows[(cell, "E", i)].get("e_compliant") is not True]
        for arm in arms:
            entry = {"by_family": {}}
            for fam in FAMILIES:
                det = metric(fam, cell, arm, "det")
                bf = entry["by_family"][fam] = {
                    "detection_mean": statistics.fmean(v[0] for v in det.values()),
                    "seen_mean": statistics.fmean(v[0] for v in metric(fam, cell, arm, "seen").values()),
                    "unsupported_mean": statistics.fmean(v[0] for v in metric(fam, cell, arm, "unsup").values()),
                }
                if arm != "N":
                    bf["detection_vs_N"] = corrected(S, det, metric(fam, cell, "N", "det"),
                                                     fsd(cell, (arm, "N"), fam, "detection", "sup" if sensitive else ""),
                                                     0.025 / len(ARMS))
                    bf["unsupported_vs_N"] = corrected(S, metric(fam, cell, arm, "unsup"), metric(fam, cell, "N", "unsup"),
                                                       fsd(cell, (arm, "N"), fam, "unsupported", "ni" if sensitive else ""),
                                                       0.05 / len(ARMS))
                    bf["unsupported_vs_N_floor_x1.5"] = corrected(
                        S, metric(fam, cell, arm, "unsup"), metric(fam, cell, "N", "unsup"),
                        fsd(cell, (arm, "N"), fam, "unsupported", "sup"), 0.05 / len(ARMS))  # reported only
            c, r = source(cell, arm)
            false_alarms = [i for i in clean if all(
                grades[(fam, c, r, i)]["unsupported"] or grades[(fam, c, r, i)]["hard_negatives_violated"]
                for fam in FAMILIES)]
            entry["clean_false_alarms_both"] = false_alarms
            entry["detection_mean"] = statistics.fmean(entry["by_family"][f]["detection_mean"] for f in FAMILIES)
            entry["tokens_median"] = statistics.median(tokens(cell, arm))
            entry["tokens_noncache_median"] = statistics.median(tokens(cell, arm, "tokens_noncache"))
            entry["seconds_median"] = statistics.median(tokens(cell, arm, "seconds"))
            entry["provider"] = source(cell, arm)[0]
            if arm != "N":
                bf = entry["by_family"]
                entry["superior_both"] = all(bf[f]["detection_vs_N"]["lo"] > 0 for f in FAMILIES)
                entry["noninferior_both"] = all(bf[f]["unsupported_vs_N"]["hi"] < 0.5 for f in FAMILIES)
                entry["qualifies"] = (entry["superior_both"] and entry["noninferior_both"] and not false_alarms
                                      and not (arm == "E" and len(doc["e_noncompliant"]) > 2))
            doc["arms"][arm] = entry
        qualified = [x for x in arms if x != "N" and doc["arms"][x].get("qualifies")]
        if not qualified:
            doc["pick"], doc["reason"] = "N", "no arm qualified: keep one native fresh-context design review (N)"
            return doc

        def equivalent(x, y):
            classes = [S.compare(metric(f, cell, x, "det"), metric(f, cell, y, "det"), 0.10,
                                 floor_sd=fsd(cell, (x, y), f, "detection", ""))["class"] for f in FAMILIES]
            return S.agree(*classes) == "equivalent"

        top = max(doc["arms"][x]["detection_mean"] for x in qualified)
        leaders = [x for x in qualified if abs(doc["arms"][x]["detection_mean"] - top) < 1e-12]
        best = leaders[0]
        if len(leaders) > 1 and not all(equivalent(x, best) for x in leaders[1:]):
            doc["pick"], doc["reason"] = None, f"unresolved: {leaders} tie at the top without equivalence"
            return doc
        pool = [best] + [x for x in qualified if x != best and equivalent(x, best)]
        own = [x for x in pool if doc["arms"][x]["provider"] == cell]
        ranked = own or pool  # X runs on another provider: its tokens are not comparable with this cell's
        cheapest = min(doc["arms"][x]["tokens_median"] for x in ranked)
        picks = [x for x in ranked if doc["arms"][x]["tokens_median"] == cheapest]
        if len(picks) > 1:
            doc["pick"], doc["reason"] = None, f"unresolved: {picks} tie on cost"
            return doc
        doc["pick"], doc["best"], doc["equivalent_pool"] = picks[0], best, pool
        doc["reason"] = f"cheapest on this provider of {pool} (best {best})"
        return doc

    result = {"status": "decided", "defect_cases": defect, "clean_cases": clean, "spec_sha256": spec_sha,
              "multiplicity": f"Bonferroni over {list(ARMS)} per cell", "cells": {}}
    for cell in ("claude", "codex"):
        primary, sensitive = decide(cell, False), decide(cell, True)
        primary["sensitivity_pick"] = sensitive.get("pick")
        if primary.get("pick") is not None and sensitive.get("pick") != primary["pick"]:
            primary["reason"] = (f"unresolved: the pick {primary['pick']} changes to {sensitive.get('pick')} in the "
                                 f"floor sensitivity run")
            primary["pick"] = None
        result["cells"][cell] = primary
    json.dump(result, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for cell, doc in result["cells"].items():
        print(cell, "pick:", doc.get("pick"), "-", doc.get("reason"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
