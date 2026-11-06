"""V4 of PREREG.md: agreement between grader families and re-judgment under each grader.

  python3 v4_compare.py <records dir> <out.json>

Agreement: Cohen's kappa on per-item labels (code map and court: fact labels; EGM: each planted defect detected or
not), Spearman on wrong-claim counts. Pairs: Opus vs Codex (original order), Codex original vs reversed, and Opus A vs
Opus B where a second Opus grading exists (Haiku). Re-judgment of the code-map foods under Opus, Codex and the
consensus (a fact is present only if both say present; wrong claims averaged) with the four-class rules (v1), and
the ledger's D29 quality rule (judge_haiku3.py thresholds) with Opus as grading A and Codex as grading B.
"""
import importlib.util
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("v1", os.path.join(HERE, "v1_resolution.py"))
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)
CONDS = {"opus": "opus-5-5", "sonnet": "sonnet-5-5", "opus48": "opus-4-8", "haiku": "haiku-5-5"}
ARMS = {"C": "codegraph", "G": "graphify", "S": "OAW code map"}
COST = {"opus-5-5": {"C": 1.200}, "sonnet-5-5": {"C": 1.308}, "opus-4-8": {"C": 1.722}, "haiku-5-5": {"C": 1.585}}


def load(path):
    if not os.path.exists(path):
        return {}
    return {g["key"]: g for g in (json.loads(l) for l in open(path, encoding="utf-8") if l.strip())}


def kappa(pairs):
    return v1_kappa(pairs)


def v1_kappa(pairs):
    if not pairs:
        return None
    cats = sorted({x for p in pairs for x in p})
    n = len(pairs)
    po = sum(1 for a, b in pairs if a == b) / n
    pe = sum((sum(1 for a, _ in pairs if a == c) / n) * (sum(1 for _, b in pairs if b == c) / n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    if len(xs) < 3:
        return None
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 3) if den else None


def fact_agreement(ga, gb):
    pairs, wa, wb = [], [], []
    for key in sorted(set(ga) & set(gb)):
        la, lb = ga[key]["verdict"].get("facts") or {}, gb[key]["verdict"].get("facts") or {}
        for fid in sorted(set(la) | set(lb)):
            pairs.append((la.get(fid, "missing"), lb.get(fid, "missing")))
        a, b = ga[key]["verdict"].get("wrong_claims"), gb[key]["verdict"].get("wrong_claims")
        if a is not None and b is not None:
            wa.append(a)
            wb.append(b)
    return {"answers": len(set(ga) & set(gb)), "labels": len(pairs),
            "raw_agreement": round(sum(1 for a, b in pairs if a == b) / len(pairs), 3) if pairs else None,
            "kappa": kappa(pairs), "wrong_spearman": spearman(wa, wb),
            "wrong_total": [sum(wa), sum(wb)]}


def egm_agreement(ga, gb):
    pairs, ua, ub = [], [], []
    for key in sorted(set(ga) & set(gb)):
        ids = ("C1", "C2", "M1", "M2") if key.split("|")[1] != "clean" else ()
        for rid in ids:
            pairs.append((rid in ga[key]["detected"], rid in gb[key]["detected"]))
        ua.append(ga[key]["unsupported"])
        ub.append(gb[key]["unsupported"])
    return {"reports": len(set(ga) & set(gb)), "labels": len(pairs),
            "raw_agreement": round(sum(1 for a, b in pairs if a == b) / len(pairs), 3) if pairs else None,
            "kappa": kappa(pairs), "unsupported_total": [sum(ua), sum(ub)]}


def consensus(ga, gb, questions):
    out = {}
    for key in set(ga) & set(gb):
        qid = key.split("|")[1]
        facts = questions[qid]["facts"]
        la, lb = ga[key]["verdict"].get("facts") or {}, gb[key]["verdict"].get("facts") or {}
        present = [f for f in facts if la.get(f["id"]) == "present" and lb.get(f["id"]) == "present"]
        wa, wb = ga[key]["verdict"].get("wrong_claims") or 0, gb[key]["verdict"].get("wrong_claims") or 0
        out[key] = {"key": key, "coverage": round(len(present) / len(facts), 3),
                    "essential_ok": all(la.get(f["id"]) == "present" and lb.get(f["id"]) == "present"
                                        for f in facts if f.get("essential")),
                    "contradicted": 0, "verdict": {"wrong_claims": (wa + wb) / 2}}
    return out


def four_class(rows, grades):
    key = lambda r: f"{r['arm']}|{r['id']}|{r['rep']}"
    cov = v1.cells(rows, grades, key, lambda r, g: g["coverage"])
    wrong = v1.cells(rows, grades, key, lambda r, g: g["verdict"].get("wrong_claims") or 0)
    out = {}
    for arm in ARMS:
        c = v1.compare(cov[arm], cov["N"], 0.10)
        w = v1.compare(wrong[arm], wrong["N"], 0.5, lower_is_better=True)
        out[arm] = {"quality": v1.quality(c, w), "coverage_point": c["point"], "coverage_class": c["class"],
                    "wrong_point": w["point"], "wrong_class": w["class"]}
    return out


def ledger_quality(rows, grades):
    """judge_haiku3.py quality rule (the ledger's D29 per-grading thresholds)."""
    spec2 = importlib.util.spec_from_file_location(
        "cg_summary", os.path.join(HERE, "..", "..", "digestion-2026-11-06", "taste-codegraph", "summary.py"))
    summary = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(summary)
    s = summary.describe(rows, grades)
    out = {}
    for arm in ARMS:
        x, n = s[arm], s["N"]
        shared = sorted(set(x["per_question"]) & set(n["per_question"]))
        dcov = x["coverage_mean"] - n["coverage_mean"]
        not_lower = sum(1 for q in shared if x["per_question"][q]["coverage"] >= n["per_question"][q]["coverage"])
        rate = lambda t: t["essential_ok_runs"] / t["runs"] if t["runs"] else 0.0
        if dcov <= -0.10 or x["wrong_claims"] >= n["wrong_claims"] + 3 or x["cutoffs"] >= n["cutoffs"] + 3:
            q = "worse"
        elif (dcov >= 0.10 and not_lower >= 3) or rate(x) >= rate(n) + 0.25:
            q = "better"
        else:
            q = "same"
        out[arm] = {"quality": q, "dcov": round(dcov, 3), "wrong": [x["wrong_claims"], n["wrong_claims"]]}
    return out


def main(records, out_path):
    cg = os.path.join(records, "digestion-2026-11-06", "taste-codegraph")
    questions = {q["id"]: q for q in json.load(open(os.path.join(
        records, "digestion-2026-11-03", "taste-graphify", "erpnext", "questions.json"), encoding="utf-8"))["questions"]}
    report = {"codemap": {}, "egm": {}, "court": {}}
    for folder, cond in CONDS.items():
        rows = [json.loads(l) for l in open(os.path.join(cg, f"out-{folder}", "rows.jsonl"), encoding="utf-8")]
        opus = load(os.path.join(cg, f"out-{folder}", "grades.jsonl"))
        cx = load(os.path.join(HERE, "v4", folder, "grades-codex-original.jsonl"))
        cxr = load(os.path.join(HERE, "v4", folder, "grades-codex-reversed.jsonl"))
        item = {"agreement": {"opus_vs_codex": fact_agreement(opus, cx), "codex_original_vs_reversed": fact_agreement(cx, cxr)}}
        if folder == "haiku":
            item["agreement"]["opus_A_vs_opus_B"] = fact_agreement(opus, load(os.path.join(cg, "out-haiku", "grades-b.jsonl")))
        if len(cx) == len(rows):
            item["four_class"] = {"opus": four_class(rows, opus), "codex": four_class(rows, cx),
                                  "consensus": four_class(rows, consensus(opus, cx, questions))}
            la, lb = ledger_quality(rows, opus), ledger_quality(rows, cx)
            item["ledger_d29_quality"] = {arm: {"opus": la[arm], "codex": lb[arm],
                                                "double_graded": la[arm]["quality"] if la[arm]["quality"] == lb[arm]["quality"] else "same"}
                                          for arm in ARMS}
        report["codemap"][cond] = item
    egm_old = os.path.join(records, "digestion-2026-11-06", "egm-selftest", "out", "grades.jsonl")
    report["egm"] = {"opus_vs_codex": egm_agreement(load(egm_old), load(os.path.join(HERE, "v4", "egm", "grades-codex-original.jsonl"))),
                     "codex_original_vs_reversed": egm_agreement(load(os.path.join(HERE, "v4", "egm", "grades-codex-original.jsonl")),
                                                                 load(os.path.join(HERE, "v4", "egm", "grades-codex-reversed.jsonl")))}
    ct = os.path.join(records, "digestion-2026-11-03", "taste-court-skill")
    court_opus = {**load(os.path.join(ct, "out", "grades.jsonl")), **load(os.path.join(ct, "out-c5", "grades.jsonl"))}
    court_cx = load(os.path.join(HERE, "v4", "court", "grades-codex-original.jsonl"))
    bl = [(court_opus[k]["verdict"].get("bottom_line"), court_cx[k]["verdict"].get("bottom_line")) for k in set(court_opus) & set(court_cx)]
    report["court"] = {"opus_vs_codex": fact_agreement(court_opus, court_cx),
                       "codex_original_vs_reversed": fact_agreement(court_cx, load(os.path.join(HERE, "v4", "court", "grades-codex-reversed.jsonl"))),
                       "bottom_line_agreement": f"{sum(1 for a, b in bl if a == b)}/{len(bl)}",
                       "coverage_by_arm": {g: {arm: round(statistics.mean(x["coverage"] for k, x in grades.items() if x["arm"] == arm), 3)
                                               for arm in ("N", "P", "C")} for g, grades in (("opus", court_opus), ("codex", court_cx))}}
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1)
    for cond, item in report["codemap"].items():
        print(cond, json.dumps(item["agreement"]))
        if "four_class" in item:
            print("  4class", {g: {a: v["quality"] for a, v in r.items()} for g, r in item["four_class"].items()})
            print("  d29q", {a: (v["opus"]["quality"], v["codex"]["quality"], v["double_graded"]) for a, v in item["ledger_d29_quality"].items()})
    print("egm", json.dumps(report["egm"]))
    print("court", json.dumps(report["court"]))


if __name__ == "__main__":
    main(*sys.argv[1:3])
