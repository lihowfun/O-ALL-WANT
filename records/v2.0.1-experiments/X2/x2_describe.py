"""X2 descriptive results (PREREG.md "只描述、不判定"). Nothing here enters the decision; x2_judge.py decides.

Per cell and arm, from the main rows and the four graders' grades:
- detection rate on the 16 primary defect cases (point means) and the mention rate (detected + mentioned_only);
- detection by case author family (opus-written vs codex-written cases);
- unsupported claims per report on the 20 primary cases; clean-case false alarms (hard negatives violated);
- logical tokens, non-cache tokens, seconds and reviewer launches (median, total);
- the descriptive cases events and clean, arm by arm;
- grader agreement on (report, planted defect) detected yes/no: luna and haiku against opus and codex, with
  opus against codex as the reference; and each grader's arm means, to see whether the cheap graders rank arms alike;
- spend: Claude logical tokens (freeze + calibration + main + usage-limit deviations + Claude grading) and Codex.

    python3 x2_describe.py --cases CASES --runs RUNS --grades GRADES_DIR --spent-at-freeze N --out describe.json
"""
import argparse
import json
import os
import statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
FAMILIES = ("opus", "codex", "luna", "haiku")


def load(path):
    return [json.loads(line) for line in open(path, encoding="utf-8")] if os.path.exists(path) else []


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None, None
    agree = sum(a == b for a, b in pairs) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return round(agree, 3), (round((agree - expected) / (1 - expected), 3) if expected < 1 else None)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--cases", required=True)
    p.add_argument("--runs", required=True)
    p.add_argument("--grades", required=True)
    p.add_argument("--spent-at-freeze", type=int, required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    spec = json.load(open(os.path.join(a.cases, "spec.json"), encoding="utf-8"))
    author = {}
    for name in ("categories.json", "categories-2.json"):
        for case in json.load(open(os.path.join(HERE, name), encoding="utf-8"))["cases"]:
            author[case["id"]] = (case["author"], case["kind"])
    primary = [c for c in spec["planned_primary"] if c not in spec.get("dropped", [])]
    defect = [c for c in primary if author[c][1] == "defect"]
    rows = {}
    for cell in ("claude", "codex"):
        for part in ("a", "b"):
            for r in load(os.path.join(a.runs, f"{cell}-{part}", "rows.jsonl")):
                rows[(cell, r["arm"], r["id"])] = r
    grades = {f: {(g["cell"], g["arm"], g["id"]): g for g in load(os.path.join(a.grades, f"main-grades-{f}.jsonl"))}
              for f in FAMILIES}
    out = {"primary_cases": len(primary), "defect_cases": len(defect), "arms": {}, "descriptive_cases": {},
           "agreement": {}, "spend": {}}

    for cell in ("claude", "codex"):
        for arm in ("N", "R", "E"):
            key = f"{cell}:{arm}"
            entry = {}
            runs = [rows[(cell, arm, c)] for c in primary if (cell, arm, c) in rows]
            entry["runs"] = len(runs)
            for field in ("tokens_total", "tokens_noncache", "seconds", "agents"):
                values = [r.get(field) or 0 for r in runs]
                entry[field] = {"median": statistics.median(values) if values else None, "total": sum(values)}
            if arm == "E":
                entry["e_compliant"] = sum(1 for r in runs if r.get("e_compliant"))
                paths = defaultdict(int)
                for r in runs:
                    for path in r.get("agent_paths") or []:
                        paths[path] += 1
                entry["agent_paths"] = dict(sorted(paths.items()))
            for fam in FAMILIES:
                g = grades[fam]
                have = [c for c in defect if (cell, arm, c) in g]
                det = [len(g[(cell, arm, c)]["detected"]) / g[(cell, arm, c)]["planted"] for c in have]
                men = [len(set(g[(cell, arm, c)]["detected"]) | set(g[(cell, arm, c)]["mentioned_only"]))
                       / g[(cell, arm, c)]["planted"] for c in have]
                by_author = {}
                for fam_author in ("opus", "codex"):
                    sub = [len(g[(cell, arm, c)]["detected"]) / g[(cell, arm, c)]["planted"]
                           for c in have if author[c][0] == fam_author]
                    by_author[fam_author] = round(statistics.fmean(sub), 3) if sub else None
                allp = [c for c in primary if (cell, arm, c) in g]
                uns = [g[(cell, arm, c)]["unsupported"] for c in allp]
                clean_alarms = sum(len(g[(cell, arm, c)]["hard_negatives_violated"]) for c in allp if author[c][1] == "clean")
                entry[fam] = {"graded_defect": len(have), "detection": round(statistics.fmean(det), 3) if det else None,
                              "mention": round(statistics.fmean(men), 3) if men else None, "by_author": by_author,
                              "unsupported_per_report": round(statistics.fmean(uns), 3) if uns else None,
                              "clean_hard_negatives_violated": clean_alarms,
                              "per_case": {c: len(g[(cell, arm, c)]["detected"]) for c in have}}
            out["arms"][key] = entry
        for case in spec["descriptive"]:
            for arm in ("N", "R", "E"):
                r = rows.get((cell, arm, case))
                d = {"tokens": r and r.get("tokens_total"), "agents": r and r.get("agents")}
                for fam in FAMILIES:
                    g = grades[fam].get((cell, arm, case))
                    if g:
                        d[fam] = {"detected": f"{len(g['detected'])}/{g['planted']}", "mentioned_only": len(g["mentioned_only"]),
                                  "unsupported": g["unsupported"], "hard_negatives_violated": len(g["hard_negatives_violated"])}
                out["descriptive_cases"][f"{cell}:{arm}:{case}"] = d

    def items(fam):
        result = {}
        for key, g in grades[fam].items():
            if key[2] not in defect:
                continue
            ids = [rid for rid, group in ((rid, grp) for grp in ("critical", "major")
                                           for rid in [f"{grp[0].upper()}{i + 1}" for i in range(len(spec["rubric"][key[2]][grp]))])]
            for rid in ids:
                result[(key, rid)] = rid in g["detected"]
        return result

    item_sets = {f: items(f) for f in FAMILIES}
    for x, y in (("opus", "codex"), ("luna", "opus"), ("luna", "codex"), ("haiku", "opus"), ("haiku", "codex")):
        common = sorted(set(item_sets[x]) & set(item_sets[y]))
        agree, k = kappa([(item_sets[x][i], item_sets[y][i]) for i in common])
        shared = sorted(set(grades[x]) & set(grades[y]))
        ux = [grades[x][r]["unsupported"] for r in shared]
        uy = [grades[y][r]["unsupported"] for r in shared]
        out["agreement"][f"{x}~{y}"] = {
            "items": len(common), "agreement": agree, "kappa": k, "reports": len(shared),
            "unsupported_exact": round(sum(p == q for p, q in zip(ux, uy)) / len(shared), 3) if shared else None,
            "unsupported_mean_abs_diff": round(statistics.fmean(abs(p - q) for p, q in zip(ux, uy)), 3) if shared else None,
            "unsupported_any_agree": round(sum((p > 0) == (q > 0) for p, q in zip(ux, uy)) / len(shared), 3) if shared else None}

    claude_cal = sum(r.get("tokens_total") or 0 for r in load(os.path.join(a.runs, "cal-claude", "rows.jsonl")))
    codex_cal = sum(r.get("tokens_total") or 0 for r in load(os.path.join(a.runs, "cal-codex", "rows.jsonl")))
    main = {cell: sum(r.get("tokens_total") or 0 for k, r in rows.items() if k[0] == cell) for cell in ("claude", "codex")}
    devs = {cell: sum(d.get("tokens_total") or 0 for part in ("a", "b")
                      for d in load(os.path.join(a.runs, f"{cell}-{part}", "deviations.jsonl"))) for cell in ("claude", "codex")}
    grading = {f: sum(g.get("tokens") or 0 for g in load(os.path.join(a.grades, f"main-grades-{f}.jsonl")))
               + sum(g.get("tokens") or 0 for g in load(os.path.join(a.grades, f"cal-grades-{f}.jsonl"))) for f in FAMILIES}
    out["spend"] = {
        "claude": {"at_freeze": a.spent_at_freeze, "calibration": claude_cal, "main": main["claude"],
                   "not_run_deviations": devs["claude"], "grading_opus": grading["opus"], "grading_haiku": grading["haiku"],
                   "total": a.spent_at_freeze + claude_cal + main["claude"] + devs["claude"] + grading["opus"] + grading["haiku"],
                   "cap": 60000000},
        "codex": {"calibration": codex_cal, "main": main["codex"], "not_run_deviations": devs["codex"],
                  "grading_codex": grading["codex"], "grading_luna": grading["luna"],
                  "total": codex_cal + main["codex"] + devs["codex"] + grading["codex"] + grading["luna"]}}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for key, e in out["arms"].items():
        line = " ".join(f"{f}:{e[f]['detection']}/{e[f]['mention']}/u{e[f]['unsupported_per_report']}" for f in FAMILIES)
        print(f"{key:9} runs {e['runs']:2} tok med {e['tokens_total']['median']} | {line}")
    print(json.dumps(out["agreement"]))
    print(json.dumps(out["spend"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
