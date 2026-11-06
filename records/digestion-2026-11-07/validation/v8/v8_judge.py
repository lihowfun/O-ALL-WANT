"""V8 judgment (ADDENDUM-V8.md): codegraph against native on its own question type, Opus 4.8.

  python3 v8_judge.py <rows.jsonl> <grades-opus.jsonl> <grades-codex.jsonl> <out.json>
"""
import importlib.util
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("v1", os.path.join(HERE, "..", "v1_resolution.py"))
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def d29(quality, ratio):
    if quality == "worse":
        return "excrete"
    if quality == "better":
        return "default" if ratio <= 1.5 else "optional"
    return "optional" if ratio <= 1.5 else "excrete"


def main(rows_path, opus_path, codex_path, out_path):
    rows = load(rows_path)
    key = lambda r: f"{r['arm']}|{r['id']}|{r['rep']}"
    result = {}
    for name, path in (("opus", opus_path), ("codex", codex_path)):
        grades = {g["key"]: g for g in load(path)}
        cov = v1.cells(rows, grades, key, lambda r, g: g["coverage"])
        wrong = v1.cells(rows, grades, key, lambda r, g: g["verdict"].get("wrong_claims") or 0)
        c = v1.compare(cov["C"], cov["N"], 0.10)
        w = v1.compare(wrong["C"], wrong["N"], 0.5, lower_is_better=True)
        result[name] = {"coverage": c, "wrong_claims": w, "quality": v1.quality(c, w),
                        "means": {arm: {"coverage": round(statistics.mean(x for v in cov[arm].values() for x in v), 3),
                                        "wrong_total": sum(x for v in wrong[arm].values() for x in v),
                                        "essential_ok": sum(1 for g in grades.values() if g["arm"] == arm and g["essential_ok"])}
                                  for arm in ("N", "C")}}
    tok = v1.cells(rows, {key(r): {} for r in rows}, key, lambda r, g: r["tokens_total"])
    tools = v1.cells(rows, {key(r): {} for r in rows}, key, lambda r, g: r["tool_calls"])
    secs = v1.cells(rows, {key(r): {} for r in rows}, key, lambda r, g: r["seconds"])
    med = lambda cells, arm: statistics.median(statistics.mean(v) for v in cells[arm].values())
    ratio = round(med(tok, "C") / med(tok, "N"), 3)
    result["efficiency"] = {"tokens": v1.compare(tok["C"], tok["N"], None, log_ratio=True),
                            "tool_calls": v1.compare(tools["C"], tools["N"], None, log_ratio=True),
                            "seconds": v1.compare(secs["C"], secs["N"], None, log_ratio=True),
                            "token_median_ratio": ratio,
                            "tool_median_ratio": round(med(tools, "C") / med(tools, "N"), 3),
                            "seconds_median_ratio": round(med(secs, "C") / med(secs, "N"), 3),
                            "tokens_total": {arm: sum(r["tokens_total"] for r in rows if r["arm"] == arm) for arm in ("N", "C")},
                            "codegraph_tool_calls": sum(sum(n for t, n in r["tools"].items() if "codegraph" in t.lower())
                                                        for r in rows if r["arm"] == "C")}
    qa, qb = result["opus"]["quality"], result["codex"]["quality"]
    direction = qa if qa == qb and qa in ("better", "worse") else "same"
    result["d29"] = {"quality_double_graded": direction, "cost_ratio": ratio, "outcome": d29(direction, ratio)}
    json.dump(result, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"opus": qa, "codex": qb, "d29": result["d29"],
                      "eff": {k: v for k, v in result["efficiency"].items() if "ratio" in k or k in ("tokens_total", "codegraph_tool_calls")}},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
