"""V5 judgment (PREREG.md): does EGM's gain on `events` hold over 3 seeds against 6 native runs?

  python3 v5_judge.py <old rows> <old opus grades> <old codex grades> <new rows> <new opus grades> <new codex grades> <out.json>

A run "catches" when both major planted defects M1 and M2 are in its detected list. Per grader family:
holds = E catches in all 3 runs and one-sided Fisher p < 0.05 for E (3) against N (6);
fails = N catches in >= 2 of 6, or E's third run does not catch; otherwise undetermined.
The verdict holds only if both graders say holds.
"""
import json
import sys
from math import comb


def load(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def fisher_one_sided(a, n1, b, n2):
    """P(X >= a) for X hypergeometric: n1 draws from n1+n2 with a+b successes."""
    k, total = a + b, n1 + n2
    return sum(comb(k, x) * comb(total - k, n1 - x) for x in range(a, min(k, n1) + 1)) / comb(total, n1)


def judge(rows, grades):
    caught = {}
    for row in rows:
        if row["id"] != "events":
            continue
        g = grades.get(f"{row['arm']}|events|{row['rep']}")
        if g is None:
            continue
        caught.setdefault(row["arm"], {})[row["rep"]] = {"M1", "M2"} <= set(g["detected"])
    e, n = caught.get("E", {}), caught.get("N", {})
    a, b = sum(e.values()), sum(n.values())
    p = fisher_one_sided(a, len(e), b, len(n)) if e and n else None
    if b >= 2 or (3 in e and not e[3]):
        reading = "fails"
    elif len(e) == 3 and a == 3 and p is not None and p < 0.05:
        reading = "holds"
    else:
        reading = "undetermined"
    return {"E": {str(k): v for k, v in sorted(e.items())}, "N": {str(k): v for k, v in sorted(n.items())},
            "P": {str(k): v for k, v in sorted(caught.get("P", {}).items())},
            "E_caught": f"{a}/{len(e)}", "N_caught": f"{b}/{len(n)}", "fisher_p_one_sided": p, "reading": reading}


def main(old_rows, old_opus, old_codex, new_rows, new_opus, new_codex, out):
    rows = load(old_rows) + load(new_rows)
    result = {}
    for name, paths in (("opus", (old_opus, new_opus)), ("codex", (old_codex, new_codex))):
        grades = {}
        for path in paths:
            grades.update({g["key"]: g for g in load(path)})
        result[name] = judge(rows, grades)
    result["verdict"] = ("holds" if all(result[n]["reading"] == "holds" for n in ("opus", "codex")) else
                         "fails" if any(result[n]["reading"] == "fails" for n in ("opus", "codex")) else "undetermined")
    tokens = {}
    for row in rows:
        if row["id"] == "events":
            tokens.setdefault(row["arm"], []).append(row["tokens_total"])
    result["tokens_events"] = tokens
    json.dump(result, open(out, "w", encoding="utf-8"), indent=1)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:8])
