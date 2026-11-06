"""V1 and V2 of PREREG.md: resolution, four-class re-judgment, sample-size planning and question checks.

  python3 v1_resolution.py <records dir> <out.json>

Zero model tokens. Reads the frozen rows and grades of past tastings, applies the shared statistical rules of
PREREG.md (question-paired difference, within-question stratified bootstrap, 10,000 draws, seed 20261107, 95% for
better/worse, 90% for equivalence within the margin), and flags ceiling and non-discriminating questions.
"""
import json
import math
import os
import random
import statistics
import sys
from collections import defaultdict

DRAWS = 10_000
SEED = 20261107
Z80 = 2.8  # two-sided alpha 0.05, power 0.8
LN15 = math.log(1.5)
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179}


def load(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def cells(rows, grades, key, metric):
    """{arm: {qid: [values over repeats]}} for one metric."""
    out = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grade = grades.get(key(row))
        if grade is None:
            continue
        value = metric(row, grade)
        if value is not None:
            out[row["arm"]][row["id"]].append(float(value))
    return out


def _quantile(values, p):
    ordered = sorted(values)
    i = p * (len(ordered) - 1)
    lo, hi = math.floor(i), math.ceil(i)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (i - lo)


def compare(x, n, margin, log_ratio=False, lower_is_better=False):
    """Question-paired difference of arm x against native n with bootstrap intervals and the four classes."""
    shared = sorted(q for q in set(x) & set(n) if x[q] and n[q])
    if not shared:
        return None

    def stat(xs, ns):
        if log_ratio:
            return statistics.mean(math.log(statistics.mean(xs[q]) / statistics.mean(ns[q])) for q in shared)
        return statistics.mean(statistics.mean(xs[q]) - statistics.mean(ns[q]) for q in shared)

    point = stat(x, n)
    per_q = {q: (math.log(statistics.mean(x[q]) / statistics.mean(n[q])) if log_ratio
                 else statistics.mean(x[q]) - statistics.mean(n[q])) for q in shared}
    reps = min(min(len(x[q]), len(n[q])) for q in shared)
    result = {"questions": len(shared), "min_repeats": reps, "point": round(point, 4),
              "per_question": {q: round(v, 4) for q, v in per_q.items()}}
    if len(shared) >= 2:
        sd = statistics.stdev(per_q.values())
        t = T975.get(len(shared) - 1, 1.96)
        result["question_random_ci95"] = [round(point - t * sd / math.sqrt(len(shared)), 4),
                                          round(point + t * sd / math.sqrt(len(shared)), 4)]
    if reps < 2:
        result.update({"class": "undetermined", "why": "one run per cell: within-question spread cannot be estimated"})
        return result
    rng = random.Random(SEED)
    draws = []
    for _ in range(DRAWS):
        xs = {q: [rng.choice(x[q]) for _ in x[q]] for q in shared}
        ns = {q: [rng.choice(n[q]) for _ in n[q]] for q in shared}
        draws.append(stat(xs, ns))
    lo95, hi95 = _quantile(draws, 0.025), _quantile(draws, 0.975)
    lo90, hi90 = _quantile(draws, 0.05), _quantile(draws, 0.95)
    se = statistics.stdev(draws)
    sign = -1 if lower_is_better else 1
    if log_ratio:
        cls = ("cheaper" if hi95 < 0 else "costlier_over_1.5x" if lo95 > LN15 else
               "costlier" if lo95 > 0 else "undetermined")
    else:
        better = (lo95 > 0) if sign == 1 else (hi95 < 0)
        worse = (hi95 < 0) if sign == 1 else (lo95 > 0)
        equivalent = -margin < lo90 and hi90 < margin
        cls = ("better (within margin)" if better and equivalent else "worse (within margin)" if worse and equivalent
               else "better" if better else "worse" if worse else "equivalent" if equivalent else "undetermined")
    result.update({"ci95": [round(lo95, 4), round(hi95, 4)], "ci90": [round(lo90, 4), round(hi90, 4)],
                   "se": round(se, 4), "mde": round(Z80 * se, 4), "margin": margin, "class": cls})
    if log_ratio:
        result["ratio_point"] = round(math.exp(point), 3)
        result["ratio_ci95"] = [round(math.exp(lo95), 3), round(math.exp(hi95), 3)]
    return result


def quality(cov, wrong):
    """Merge rule of PREREG.md."""
    c = (cov or {}).get("class", "undetermined")
    w = (wrong or {}).get("class", "undetermined")
    if c.startswith("worse") or w.startswith("worse"):
        return "worse"
    if c.startswith("better") and not w.startswith("worse"):
        return "better"
    if c == "equivalent" and w == "equivalent":
        return "equivalent"
    if c.startswith("better") or c.startswith("worse"):
        return c.split(" ")[0]
    return "undetermined"


def variance_parts(arms_cells):
    """Pooled within-cell variance and between-question variance of the per-question means (for planning)."""
    within, means = [], defaultdict(list)
    for arm, qs in arms_cells.items():
        for q, values in qs.items():
            if len(values) >= 2:
                within.append(statistics.variance(values))
            means[arm].append(statistics.mean(values))
    return statistics.mean(within) if within else None


def plan(sigma_w2, tau2, targets=(0.10, 0.05)):
    """Questions x repeats per arm needed for an MDE target, fixed-question and question-random."""
    table = []
    for r in (1, 3, 5):
        for q in (4, 8, 12, 20, 40, 80):
            fixed = Z80 * math.sqrt(2 * sigma_w2 / (q * r))
            rand = Z80 * math.sqrt(2 * sigma_w2 / (q * r) + tau2 / q)
            table.append({"repeats": r, "questions": q, "mde_fixed": round(fixed, 3), "mde_question_random": round(rand, 3)})
    needs = {}
    for target in targets:
        for mode in ("mde_fixed", "mde_question_random"):
            ok = [row for row in table if row[mode] <= target]
            needs[f"{mode}<={target}"] = (min(ok, key=lambda row: row["questions"] * row["repeats"]) if ok else None)
    return {"table": table, "cheapest": needs}


def codemap(records):
    base = os.path.join(records, "digestion-2026-11-06", "taste-codegraph")
    out, ceilings, var_cov, tau_cov = {}, {}, [], []
    for cond, folder, grade_files in (("opus-5-5", "out-opus", ["grades.jsonl"]),
                                      ("sonnet-5-5", "out-sonnet", ["grades.jsonl"]),
                                      ("opus-4-8", "out-opus48", ["grades.jsonl"]),
                                      ("haiku-5-5", "out-haiku", ["grades.jsonl", "grades-b.jsonl"])):
        rows = load(os.path.join(base, folder, "rows.jsonl"))
        for gfile in grade_files:
            grades = {g["key"]: g for g in load(os.path.join(base, folder, gfile))}
            key = lambda r: f"{r['arm']}|{r['id']}|{r['rep']}"
            cov = cells(rows, grades, key, lambda r, g: g["coverage"])
            wrong = cells(rows, grades, key, lambda r, g: g["verdict"].get("wrong_claims") or 0)
            tok = cells(rows, grades, key, lambda r, g: r["tokens_total"])
            label = cond + ("" if gfile == "grades.jsonl" else " (grading B)")
            out[label] = {}
            for arm in ("C", "G", "S"):
                c = compare(cov[arm], cov["N"], 0.10)
                w = compare(wrong[arm], wrong["N"], 0.5, lower_is_better=True)
                t = compare(tok[arm], tok["N"], None, log_ratio=True)
                out[label][arm] = {"coverage": c, "wrong_claims": w, "tokens": t, "quality": quality(c, w)}
            if gfile == "grades.jsonl":
                var_cov.append(variance_parts(cov))
                for arm in ("C", "G", "S"):
                    diffs = [statistics.mean(cov[arm][q]) - statistics.mean(cov["N"][q]) for q in cov["N"]]
                    tau_cov.append(statistics.variance(diffs))
                ceilings[cond] = {
                    q: {"native_min": round(min(v), 3), "ceiling": min(v) >= 0.95,
                        "no_discrimination": len({x for a in cov for x in cov[a][q]}) == 1}
                    for q, v in sorted(cov["N"].items())}
    sigma_w2 = statistics.mean(var_cov)
    tau2 = statistics.mean(tau_cov)
    return out, ceilings, {"coverage_within_variance": round(sigma_w2, 5), "coverage_between_question_variance_of_diff":
                           round(tau2, 5), "plan": plan(sigma_w2, tau2)}


def egm(records):
    base = os.path.join(records, "digestion-2026-11-06", "egm-selftest", "out")
    rows = load(os.path.join(base, "rows.jsonl"))
    grades = {g["key"]: g for g in load(os.path.join(base, "grades.jsonl"))}
    key = lambda r: f"{r['arm']}|{r['id']}|{r['rep']}"
    det = cells(rows, grades, key, lambda r, g: len(g["detected"]))
    uns = cells(rows, grades, key, lambda r, g: g["unsupported"])
    tok = cells(rows, grades, key, lambda r, g: r["tokens_total"])
    out = {}
    for arm in ("E", "P"):
        d = compare(det[arm], det["N"], 1.0)
        # Cases where both arms have zero spread and zero mean (clean) carry no information on detections.
        u = compare(uns[arm], uns["N"], 0.5, lower_is_better=True)
        t = compare(tok[arm], tok["N"], None, log_ratio=True)
        out[arm] = {"detections": d, "unsupported": u, "tokens": t, "quality": quality(d, u)}
        events = {k: v for k, v in det[arm].items() if k == "events"}
        out[arm]["detections_events_only"] = compare(events, {"events": det["N"]["events"]}, 1.0)
    planted = {"orders": 4, "events": 4, "clean": 0}
    flags = {case: {"native": det["N"][case], "planted_per_run": planted[case],
                    "ceiling": planted[case] > 0 and min(det["N"][case]) >= planted[case],
                    "no_planted_defects": planted[case] == 0,
                    "no_discrimination": len({x for a in det for x in det[a][case]}) == 1}
             for case in sorted(det["N"])}
    return out, flags


def court(records):
    base = os.path.join(records, "digestion-2026-11-03", "taste-court-skill")
    rows = load(os.path.join(base, "out", "rows.jsonl")) + load(os.path.join(base, "out-c5", "rows.jsonl"))
    grades = {g["key"]: g for g in load(os.path.join(base, "out", "grades.jsonl"))
              + load(os.path.join(base, "out-c5", "grades.jsonl"))}
    key = lambda r: f"{r['arm']}|{r['id']}|{r['rep']}"
    cov = cells(rows, grades, key, lambda r, g: g["coverage"])
    tok = cells(rows, grades, key, lambda r, g: r["tokens_total"])
    out = {arm: {"coverage": compare(cov[arm], cov["N"], 0.10), "tokens": compare(tok[arm], tok["N"], None, log_ratio=True)}
           for arm in ("C", "P")}
    flags = {case: {"native": v[0], "ceiling": v[0] >= 0.95} for case, v in sorted(cov["N"].items())}
    return out, flags


def tokeneconomizer(records):
    base = os.path.join(records, "digestion-2026-11-03", "taste-tokeneconomizer")
    rows = load(os.path.join(base, "rows.jsonl"))
    grades = {(g["arm"], g["id"]): g for g in load(os.path.join(base, "grades.jsonl"))}
    key = lambda r: (r["arm"], r["id"])
    ok = cells(rows, grades, key, lambda r, g: 1.0 if g["correct"] else 0.0)
    tok = cells(rows, grades, key, lambda r, g: r["tokens_total"])
    verify = json.load(open(os.path.join(base, "verify.json"), encoding="utf-8"))
    used = {r["id"] for r in rows}
    checked = {t["id"]: t for t in verify["tasks"]}
    return ({"T": {"correct": compare(ok["T"], ok["N"], 0.10), "tokens": compare(tok["T"], tok["N"], None, log_ratio=True)}},
            {"tasks": len(used),
             "hidden_tests_validated": all(checked.get(t, {}).get("fails_at_base") and
                                           checked.get(t, {}).get("passes_with_reference") for t in used),
             "tasks_missing_from_verify": sorted(t for t in used if t not in checked),
             "all_arms_all_correct": all(v == [1.0] for arm in ok for v in ok[arm].values())})


# Ledger verdicts on 2026-11-07 (catalog.py why) and what each rests on, for the side-by-side table.
LEDGER = {
    "codegraph": "excrete: cost (quality same), decided by opus-4-8 at 1.722x",
    "graphify": "excrete: worse (haiku-5-5, wrong claims, double-graded)",
    "OAW code map (S)": "not a food; reported optional in RESEARCH (quality same, up to 1.40x)",
    "EGM self-test": "optional (not in ledger: reserved id); E better on detections, 28x",
    "court-skill": "excrete: cost (~94x); quality same",
    "TokenEconomizer": "optional: quality same, 1.01x",
}


def main(records, out_path):
    cm, cm_flags, cm_plan = codemap(records)
    eg, eg_flags = egm(records)
    ct, ct_flags = court(records)
    te, te_flags = tokeneconomizer(records)
    names = {"C": "codegraph", "G": "graphify", "S": "OAW code map (S)"}
    rejudged = []
    for cond, arms in cm.items():
        for arm, r in arms.items():
            rejudged.append({"food": names[arm], "condition": cond, "quality_4class": r["quality"],
                             "coverage": r["coverage"]["class"], "coverage_point": r["coverage"]["point"],
                             "coverage_ci95": r["coverage"].get("ci95"), "coverage_mde": r["coverage"].get("mde"),
                             "wrong_claims": r["wrong_claims"]["class"], "wrong_point": r["wrong_claims"]["point"],
                             "tokens": r["tokens"]["class"], "token_ratio": r["tokens"].get("ratio_point"),
                             "token_ratio_ci95": r["tokens"].get("ratio_ci95")})
    for arm, r in eg.items():
        rejudged.append({"food": "EGM self-test" if arm == "E" else "EGM positive control (P)", "condition": "opus-5-5",
                         "quality_4class": r["quality"], "detections": r["detections"]["class"],
                         "detections_point": r["detections"]["point"], "detections_ci95": r["detections"].get("ci95"),
                         "detections_mde": r["detections"].get("mde"), "unsupported": r["unsupported"]["class"],
                         "tokens": r["tokens"]["class"], "token_ratio": r["tokens"].get("ratio_point")})
    for arm, r in ct.items():
        rejudged.append({"food": "court-skill" if arm == "C" else "court positive control (P)", "condition": "opus-5-5",
                         "quality_4class": r["coverage"]["class"], "coverage_point": r["coverage"]["point"],
                         "question_random_ci95": r["coverage"].get("question_random_ci95"),
                         "token_ratio_point": round(math.exp(r["tokens"]["point"]), 1)})
    rejudged.append({"food": "TokenEconomizer", "condition": "opus-5-5", "quality_4class": te["T"]["correct"]["class"],
                     "correct_point": te["T"]["correct"]["point"], "why": te["T"]["correct"].get("why"),
                     "token_ratio_point": round(math.exp(te["T"]["tokens"]["point"]), 3),
                     "token_ratio_question_random_ci95": [round(math.exp(v), 3) for v in
                                                          te["T"]["tokens"].get("question_random_ci95", [0, 0])]})
    counts = defaultdict(int)
    for item in rejudged:
        counts[item["quality_4class"]] += 1
    report = {"protocol": "PREREG.md shared rules; within-question stratified bootstrap, 10,000 draws, seed 20261107",
              "ledger": LEDGER, "rejudged": rejudged, "class_counts": dict(counts),
              "codemap": cm, "egm": eg, "court": ct, "tokeneconomizer": te,
              "planning_codemap_coverage": cm_plan,
              "v2_questions": {"codemap": cm_flags, "egm": eg_flags, "court": ct_flags, "tokeneconomizer": te_flags}}
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1)
    for item in rejudged:
        print(json.dumps(item, ensure_ascii=False))
    print("class counts", dict(counts))
    print("plan", json.dumps(cm_plan["plan"]["cheapest"], ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:3])
