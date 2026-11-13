#!/usr/bin/env python3
"""Offline D45 regression thresholds. No model, new grading, or significance claim."""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

CELLS = ("codex", "claude")
STATUSES = {"observed", "absent", "unverified"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def row_sha(row):
    return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_rows(path):
    path = Path(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def score(row):
    grade = row["grade"]
    if grade.get("error") or row.get("not_run"):
        raise ValueError("an ungraded attempt is not a counted row")
    items = grade["items"]
    if not items or any(type(v) is not bool for v in items.values()):
        raise ValueError("grade items must be nonempty booleans")
    if grade["n"] != len(items) or grade["passed"] != sum(items.values()):
        raise ValueError("grade counts disagree with items")
    if type(grade["suite_regression"]) is not bool:
        raise ValueError("suite status missing")
    value = Fraction(0) if grade["suite_regression"] else Fraction(grade["passed"], grade["n"])
    if abs(float(value) - float(row["score"])) > 1e-12:
        raise ValueError("row score disagrees with mechanical grade")
    return value


def validate_grade(row, unit):
    grade = row["grade"]
    functions = grade["functions"]
    if set(functions) != set(unit["functions"]) or any(type(v) is not bool for v in functions.values()):
        raise ValueError("hidden functions differ from frozen grader")
    items = {key: bool(members) and all(functions.get(fn, False) for fn in members)
             for key, members in unit["items"].items()}
    if grade["items"] != items:
        raise ValueError("grade items disagree with frozen function mapping")
    recall_functions = [fn for fn in unit["functions"] if fn.startswith("test_recall_")]
    recall = (all(functions[fn] for fn in recall_functions) and not grade["suite_regression"]) if recall_functions else None
    if grade.get("recall") is not recall:
        raise ValueError("recall disagrees with frozen functions and suite status")


def index_rows(rows):
    result = {}
    for row in rows:
        key = row["cell"], row["unit"], row["arm"]
        if key in result:
            raise ValueError(f"duplicate row: {key}")
        score(row)
        if type(row["tokens_total"]) is not int or row["tokens_total"] <= 0:
            raise ValueError(f"invalid token total: {key}")
        result[key] = row
    return result


def validate_new(row, manifest, unit):
    rt = manifest["runtime"]
    expected = {
        "arm": "O", "tag": "fixcheck", "arm_commit": rt["arms"]["O"]["commit"],
        "runner_sha256": rt["files"]["h1_run.py"],
        "units_sha256": rt["units"][unit["klass"]], "unit_sha256": unit["sha256"],
        "klass": unit["klass"], "model_asked": rt["launch"]["cells"][row["cell"]]["model"],
        # A custom tag has no H1 FREEZE identity; the external BINDING is mandatory.
        "freeze_sha256": "",
    }
    for key, value in expected.items():
        if row.get(key) != value:
            raise ValueError(f"{row['cell']}/{row['unit']}: {key} differs")
    if row["cell"] == "claude" and (row.get("cap") != 17_000_000 or row.get("cap_decision") != "D45"):
        raise ValueError("wrong FIXCHECK budget")
    if len(row["sessions"]) != unit["sessions"]:
        raise ValueError("missing session")
    if any(type(s.get("tokens_total")) is not int or s["tokens_total"] <= 0 for s in row["sessions"]):
        raise ValueError("session tokens must be positive integers")
    if sum(s["tokens_total"] for s in row["sessions"]) != row["tokens_total"]:
        raise ValueError("session usage disagrees with row")
    if unit["klass"] == "B" and type(row["grade"].get("recall")) is not bool:
        raise ValueError("missing recall outcome")


def event_index(events, new, manifest_hash):
    if events.get("manifest_sha256") != manifest_hash:
        raise ValueError("events belong to another manifest")
    result = {}
    for event in events["rows"]:
        key = event["cell"], event["unit"], "O"
        if key in result:
            raise ValueError(f"duplicate event row: {key}")
        if key not in new:
            if event.get("row_sha256") is not None:
                raise ValueError(f"event binds a missing row: {key}")
        elif event.get("row_sha256") not in (None, row_sha(new[key])):
            raise ValueError(f"event row digest differs: {key}")
        for name in ("M1", "M2", "M3", "R1", "R2"):
            item = event[name]
            if item["status"] not in STATUSES:
                raise ValueError("unknown mechanism status")
            if item["status"] != "unverified":
                if key not in new or event.get("row_sha256") != row_sha(new[key]):
                    raise ValueError("audited mechanism needs a bound counted row")
                if not item.get("evidence"):
                    raise ValueError("audited mechanism needs evidence")
                for ref in item["evidence"]:
                    digest = ref.get("sha256", "")
                    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                        raise ValueError("invalid evidence SHA-256")
                    if not ref.get("locator") or not ref.get("summary"):
                        raise ValueError("evidence needs locator and summary")
        result[key] = event
    return result


def evaluate(manifest, baselines, rows, events, manifest_hash):
    units = {u["id"]: u for u in manifest["units"]}
    expected = {(cell, name, "O") for cell in CELLS for name in units}
    old = index_rows(baselines["rows"])
    wanted_old = {(cell, name, arm) for cell in CELLS for name in units for arm in ("O", "N1", "N2")}
    if set(old) != wanted_old:
        raise ValueError("baseline must contain exactly both cells, all units and O/N1/N2")
    for old_row in old.values():
        validate_grade(old_row, units[old_row["unit"]])
    new = index_rows(rows)
    if set(new) - expected:
        raise ValueError("unknown cell, unit or arm")
    audit = event_index(events, new, manifest_hash)
    if set(audit) != expected:
        raise ValueError("events template must contain exactly the fixed 24 rows")
    comparisons, failures, drops, mechanisms, pending, actions = [], [], [], [], [], set()
    for cell, name, arm in sorted(expected):
        key = cell, name, arm
        if key not in new:
            pending.append(f"{cell}/{name}: missing counted row")
            continue
        now, prev, unit = new[key], old[key], units[name]
        validate_new(now, manifest, unit)
        validate_grade(now, unit)
        for field in ("functions", "items"):
            if set(now["grade"][field]) != set(prev["grade"][field]):
                raise ValueError(f"{cell}/{name}: hidden {field} set differs")
            if any(type(v) is not bool for v in now["grade"][field].values()):
                raise ValueError("hidden outcomes must be booleans")
        ns = [old[cell, name, a] for a in ("N1", "N2")]
        n_tokens = Fraction(sum(r["tokens_total"] for r in ns), 2)
        n_score = sum((score(r) for r in ns), Fraction()) / 2
        delta = score(now) - score(prev)
        changed = {field: sorted(k for k, v in prev["grade"][field].items()
                                 if v and not now["grade"][field][k]) for field in ("functions", "items")}
        forgot = prev["grade"].get("recall") is True and now["grade"].get("recall") is False
        row = {"cell": cell, "unit": name, "klass": unit["klass"], "type": unit["type"],
               "new_score": float(score(now)), "old_score": float(score(prev)), "native_mean_score": float(n_score),
               "new_tokens": now["tokens_total"], "old_tokens": prev["tokens_total"],
               "native_mean_tokens": float(n_tokens), "new_recall": now["grade"].get("recall"),
               "old_recall": prev["grade"].get("recall"), "native_recall_count": sum(r["grade"].get("recall") is True for r in ns),
               "score_delta": float(delta), "lost_hidden": changed, "forgot": forgot}
        if delta < 0 or forgot or any(changed.values()):
            drops.append(row)
        if unit["klass"] == "A":
            row["score_ok"] = delta >= 0
            row["tokens_ok"] = now["tokens_total"] <= n_tokens * Fraction(6, 5)
            if not row["score_ok"] or not row["tokens_ok"]:
                failures.append(f"{cell}/{name}: small-change threshold")
                actions.add("revert M1+M2+R2")
        elif unit["klass"] == "C":
            row["score_ok"] = delta >= -Fraction(1, 10)
            if not row["score_ok"]:
                failures.append(f"{cell}/{name}: large-change score")
                actions.add("revert R2" if unit["type"] == "design" else "block release; owner disposition for non-design C")
            if unit["type"] == "design":
                row["tokens_lower"] = now["tokens_total"] < prev["tokens_total"]
                if not row["tokens_lower"]:
                    actions.add("retain R2; report no measured token saving for each affected design unit")
        required = []
        if unit["klass"] == "B":
            required += ["M1", "M2"]
            if cell == "codex":
                required += ["M3"]
        if cell == "codex" and (unit["klass"] == "C" or audit[key].get("extra_required_review")):
            required += ["R1"]
        if unit["type"] == "design" or audit[key].get("extra_deep"):
            required += ["R2"]
        for name_m in required:
            status = audit[key][name_m]["status"]
            mechanisms.append({"cell": cell, "unit": name, "fix": name_m, "status": status})
            if status == "absent" and name_m in ("M3", "R1"):
                actions.add(f"block release; repair {name_m} against offline reproduction")
        comparisons.append(row)
    memory = []
    for cell in CELLS:
        keys = [(cell, u["id"], "O") for u in units.values() if u["klass"] == "B"]
        old_count = sum(old[k]["grade"]["recall"] for k in keys)
        new_count = sum(new[k]["grade"]["recall"] for k in keys if k in new)
        statuses = [audit[k]["M1"]["status"] for k in keys]
        ready = all(k in new for k in keys) and "unverified" not in statuses
        m1 = statuses.count("observed")
        forgotten = [k[1] for k in keys if k in new and old[k]["grade"]["recall"] and not new[k]["grade"]["recall"]]
        ok = ready and m1 >= 3 and new_count >= old_count and not forgotten
        memory.append({"cell": cell, "complete": ready, "old_remembered": old_count, "new_remembered": new_count,
                       "M1_observed": m1, "forgotten": forgotten, "passed": ok if ready else None})
        if not ready:
            pending.append(f"{cell}: memory rows or M1 audit incomplete")
        elif not ok:
            failures.append(f"{cell}: memory threshold")
            actions.add("revert M1+M2")
    outcome = "incomplete" if pending else "fail" if failures else "pass"
    return {"numeric_outcome": outcome, "counted_rows": len(new), "expected_rows": len(expected),
            "pending": pending, "failures": failures, "actions": sorted(actions), "memory": memory,
            "comparisons": comparisons, "drops": drops, "mechanisms": mechanisms,
            "mechanisms_unverified": [r for r in mechanisms if r["status"] == "unverified"],
            "mechanisms_absent": [r for r in mechanisms if r["status"] == "absent"],
            "claim": "這次作答符合事先定的回歸門檻" if outcome == "pass" else None,
            "limitation": "Same diagnostic tasks, one counted answer each; not independent effectiveness evidence. "
                          "Numeric pass does not replace mechanism audit, offline probes, CI or release review."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--baselines", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--events", type=Path, required=True)
    args = p.parse_args()
    try:
        manifest, baselines = read_json(args.manifest), read_json(args.baselines)
        if sha(args.baselines) != manifest["baseline_sha256"]:
            raise ValueError("baseline digest differs")
        if read_json(args.state / "BINDING.json")["manifest_sha256"] != sha(args.manifest):
            raise ValueError("state belongs to another manifest")
        rows = [r for c in CELLS for r in read_rows(args.state / f"rows-fixcheck-{c}.jsonl")]
        out = evaluate(manifest, baselines, rows, read_json(args.events), sha(args.manifest))
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return {"pass": 0, "fail": 1, "incomplete": 2}[out["numeric_outcome"]]
    except (KeyError, TypeError, ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc), "numeric_outcome": "invalid"}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
