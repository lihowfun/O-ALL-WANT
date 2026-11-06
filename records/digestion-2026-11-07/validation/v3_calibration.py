"""V3 of PREREG.md: grader calibration on answers whose correct grade is known.

  python3 v3_calibration.py build <questions.json> <native rows.jsonl> <out dir>
  python3 v3_calibration.py score <out dir> <grades.jsonl> [<grades.jsonl> ...]

`build` writes <out dir>/rows.jsonl (24 answers: variants a-f for each of the 4 ERPNext questions) and
<out dir>/expected.json. The planted wrong statements are fixed below, before any grading. `score` compares each
grade file with the expectations and every pair of grade files with each other.
"""
import json
import os
import sys
from itertools import combinations

# Two sentences per question that name files or functions playing no part in the reference facts (variant f).
PLANTED = {
    "q1": ["Also, `erpnext/crm/doctype/lead/lead.py::Lead.create_prospect_and_contact` calls update_bin_qty with only "
           "{'reserved_qty': ...} whenever a lead is converted, so lead conversion breaks too.",
           "Finally, `erpnext/accounts/doctype/payment_entry/payment_entry.py::PaymentEntry.on_submit` calls "
           "update_bin_qty with an empty dict to refresh stock after every payment, so every payment submission fails."],
    "q2": ["Also, `erpnext/selling/doctype/quotation/quotation.py::Quotation.validate` calls get_valuation_rate "
           "without the argument, so saving a Quotation for an item with no rate would now silently use zero.",
           "Finally, `erpnext/crm/doctype/opportunity/opportunity.py::Opportunity.validate` relies on the default too "
           "and would stop raising when an item has no rate."],
    "q3": ["Before booking, the job also calls `erpnext/stock/doctype/stock_reconciliation/stock_reconciliation.py::"
           "StockReconciliation.make_gl_entries` to revalue inventory for each deferred item.",
           "In addition, `erpnext/selling/doctype/sales_order/sales_order.py::SalesOrder.on_submit` creates a Process "
           "Deferred Accounting document for each submitted order."],
    "q4": ["After it is returned, `erpnext/accounts/doctype/pricing_rule/pricing_rule.py::apply_pricing_rule` also "
           "overrides the cost_center on the row.",
           "Finally, `erpnext/setup/doctype/company/company.py::Company.validate_cost_center_for_item` re-checks the "
           "result on every row before it is shown."],
}
SWAP = {"q1": "q2", "q2": "q1", "q3": "q4", "q4": "q3"}
NOTHING = "I could not determine this from the repository."


def _facts_text(facts):
    return "Here is what the code shows.\n\n" + "\n".join(f"- {f['fact']} ({f.get('where', '')})" for f in facts)


def build(questions_path, native_rows, out_dir):
    questions = {q["id"]: q for q in json.load(open(questions_path, encoding="utf-8"))["questions"]}
    native = {r["id"]: r for r in (json.loads(l) for l in open(native_rows, encoding="utf-8"))
              if r["arm"] == "N" and r["rep"] == 1}
    rows, expected = [], {}
    for qid, q in sorted(questions.items()):
        facts = q["facts"]
        odd = [f for i, f in enumerate(facts) if i % 2 == 0]  # q?f1, q?f3, ... (1-based odd ids)
        answers = {
            "a": (_facts_text(facts), {f["id"]: "present" for f in facts}, {"wrong": 0}),
            "b": (_facts_text(odd), {f["id"]: ("present" if f in odd else "absent") for f in facts}, {"wrong": 0}),
            "c": (NOTHING, {f["id"]: "absent" for f in facts}, {"wrong": 0}),
            "d": (_facts_text(questions[SWAP[qid]]["facts"]), {f["id"]: "absent" for f in facts}, {"wrong_at_least": 1}),
            "e": (native[qid]["answer"], None, {}),
            "f": (native[qid]["answer"].rstrip() + "\n\n" + " ".join(PLANTED[qid]), None, {"wrong_over_e": 2}),
        }
        for variant, (text, labels, wrong) in answers.items():
            rows.append({"arm": variant, "id": qid, "rep": 1, "answer": text})
            expected[f"{variant}|{qid}|1"] = {"labels": labels, **wrong}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "rows.jsonl"), "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(os.path.join(out_dir, "expected.json"), "w", encoding="utf-8") as handle:
        json.dump(expected, handle, ensure_ascii=False, indent=1)
    print(f"{len(rows)} calibration answers written")


def _kappa(pairs):
    if not pairs:
        return None
    cats = sorted({x for p in pairs for x in p})
    n = len(pairs)
    po = sum(1 for a, b in pairs if a == b) / n
    pe = sum((sum(1 for a, _ in pairs if a == c) / n) * (sum(1 for _, b in pairs if b == c) / n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def score(out_dir, grade_paths):
    expected = json.load(open(os.path.join(out_dir, "expected.json"), encoding="utf-8"))
    files = {}
    for path in grade_paths:
        files[os.path.basename(path)] = {g["key"]: g for g in (json.loads(l) for l in open(path, encoding="utf-8"))}
    report = {"per_grader": {}, "agreement": {}}
    for name, grades in files.items():
        right = total = 0
        by_variant = {}
        wrong_checks = {"a_wrong_is_0": [], "b_wrong_is_0": [], "c_wrong_is_0": [], "d_wrong_at_least_1": []}
        planted, ef_same = [], []
        for key, exp in expected.items():
            g = grades.get(key)
            if not g:
                continue
            variant = key.split("|")[0]
            labels = g["verdict"].get("facts") or {}
            wrong = g["verdict"].get("wrong_claims")
            if exp["labels"]:
                hits = sum(1 for fid, lab in exp["labels"].items() if labels.get(fid) == lab)
                right += hits
                total += len(exp["labels"])
                by_variant.setdefault(variant, [0, 0])
                by_variant[variant][0] += hits
                by_variant[variant][1] += len(exp["labels"])
            if variant in ("a", "b", "c"):
                wrong_checks[f"{variant}_wrong_is_0"].append(wrong == 0)
            if variant == "d":
                wrong_checks["d_wrong_at_least_1"].append((wrong or 0) >= 1)
            if variant == "f":
                e = grades.get(key.replace("f|", "e|", 1))
                if e:
                    delta = (wrong or 0) - (e["verdict"].get("wrong_claims") or 0)
                    planted.append(delta)
                    el = e["verdict"].get("facts") or {}
                    ef_same.append(sum(1 for fid in el if el.get(fid) == labels.get(fid)) / max(len(el), 1))
        report["per_grader"][name] = {
            "label_accuracy_a_to_d": round(right / total, 3) if total else None,
            "label_accuracy_by_variant": {v: round(h / t, 3) for v, (h, t) in sorted(by_variant.items())},
            "wrong_claim_checks": {k: f"{sum(v)}/{len(v)}" for k, v in wrong_checks.items()},
            "planted_wrong_delta_f_minus_e": planted,
            "planted_detected_rate": round(sum(1 for d in planted if d >= 2) / len(planted), 3) if planted else None,
            "planted_partial_or_better_rate": round(sum(1 for d in planted if d >= 1) / len(planted), 3) if planted else None,
            "e_f_label_consistency": round(sum(ef_same) / len(ef_same), 3) if ef_same else None,
            "graded": len(grades),
        }
        acc = report["per_grader"][name]["label_accuracy_a_to_d"]
        det = report["per_grader"][name]["planted_detected_rate"]
        report["per_grader"][name]["reading"] = (
            "wrong-claim counts of this grader must not decide a verdict alone"
            if (acc is not None and acc < 0.90) or (det is not None and det < 0.75) else "passes the PREREG bar")
    for (na, ga), (nb, gb) in combinations(sorted(files.items()), 2):
        pairs, wrong_pairs = [], []
        for key in sorted(set(ga) & set(gb)):
            la, lb = ga[key]["verdict"].get("facts") or {}, gb[key]["verdict"].get("facts") or {}
            for fid in sorted(set(la) | set(lb)):
                pairs.append((la.get(fid, "missing"), lb.get(fid, "missing")))
            wrong_pairs.append((ga[key]["verdict"].get("wrong_claims"), gb[key]["verdict"].get("wrong_claims")))
        report["agreement"][f"{na} vs {nb}"] = {
            "fact_labels": len(pairs), "raw_agreement": round(sum(1 for a, b in pairs if a == b) / len(pairs), 3) if pairs else None,
            "kappa": _kappa(pairs), "wrong_claims_equal": f"{sum(1 for a, b in wrong_pairs if a == b)}/{len(wrong_pairs)}"}
    with open(os.path.join(out_dir, "score.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1)
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(*sys.argv[2:5])
    else:
        score(sys.argv[2], sys.argv[3:])
