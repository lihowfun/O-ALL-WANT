"""I16 calibration and decision (PREREG.md), with OAW's own yardstick (scripts/eval_stats.py, D29 and D32).

calibrate: from N run 3 times on each defect journey in each cell, graded by both families:
  - ceiling: a defect journey whose planted defect N detected in all 3 runs, in both cells, by both families, is at
    the ceiling and must be replaced before the main runs (D32 item 3; EVAL_PROTOCOL "原生已經接近滿分的題目要換掉");
  - floors: per cell and family, the pooled within-journey SD of detection and of unsupported findings
    (eval_stats.pooled_within_sd), never below the borrowed X2 values (calibration can raise a floor, not lower it).
judge: per cell, F against N (and D against N, descriptive):
  - detection on the defect journeys: compare(margin 0.10), per family; unsupported findings per report on all
    journeys: compare(margin 0.5, lower is better), per family; quality() per family, agree() across families;
  - Codex's frozen BASH rule on top: F counts as better only with zero missed planted critical defects (both families
    must credit every critical one); otherwise better becomes undetermined;
  - cost: eval_stats.cost on logical tokens per journey (F over N);
  - outcome per cell by EVAL_PROTOCOL's table; the two cells' lowest outcome decides (D29);
  - the BASH pass flag, Codex's frozen acceptance test, computed apart from the D29 class: both families find detection
    better, both families' 95% upper bound of (F - N) unsupported findings per report is below 0.5, zero missed planted
    critical defects, and the cost ratio's 95% upper bound is at most 1.5. "default" needs BASH to pass in both
    cells; a D29 "default" without it becomes "optional".

    python3 i16_judge.py calibrate --eval-stats eval_stats.py --cases FROZEN --rows cal-claude,cal-codex \
        --grades cal-opus,cal-codex --replay cal-replay.jsonl --borrowed floor.json --out floor-final.json
    python3 i16_judge.py judge --eval-stats eval_stats.py --cases FROZEN --floor floor-final.json \
        --rows claude-rows,codex-rows --grades opus,codex --replay replay.jsonl --out judge.json
"""
import argparse
import hashlib
import importlib.util
import json
import os
import statistics
import sys

FAMILIES = ("opus", "codex")
CELLS = ("claude", "codex")
OUTCOME_ORDER = ("excrete", "optional", "default")


def load_stats(path):
    spec = importlib.util.spec_from_file_location("eval_stats", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def read(paths):
    return [json.loads(l) for p in paths.split(",") for l in open(p, encoding="utf-8")]


def bind(spec, spec_sha, rows, grades, replay_path, whole_spec=True):
    """Every stage bound end to end. Rows: one runner version, one prompt per arm, case and built-tool digests equal
    to the spec (and the spec itself when whole_spec; calibration binds by case digest so a replaced journey does
    not void the others). Grades: the row's report and runner, the replay content shown for that report (recomputed
    from the replay file), one grader and one replayer version per family, no duplicates."""
    by_key, runners, prompts = {}, set(), {}
    for r in rows:
        key = f"{r['cell']}|{r['arm']}|{r['id']}" + (f"|r{r['rep']}" if r.get("rep", 1) != 1 else "")
        if key in by_key:
            raise SystemExit(f"duplicate row {key}")
        if whole_spec and r.get("spec_sha256") != spec_sha:
            raise SystemExit(f"{key}: row from another spec")
        if r.get("case_digest") != spec["case_digests"].get(r["id"]) or r.get("built_digest") != spec["built_digests"].get(r["id"]):
            raise SystemExit(f"{key}: row ran another case or built tool")
        runners.add(r.get("runner_sha256"))
        prompts.setdefault((r["cell"], r["arm"]), set()).add(r.get("prompt_sha256"))  # D and F name a per-host path
        by_key[key] = r
    if len(runners) > 1 or any(len(v) > 1 for v in prompts.values()):
        raise SystemExit("rows from more than one runner or prompt version")
    replays = {}
    for path in replay_path.split(","):
        for line in open(path, encoding="utf-8"):
            e = json.loads(line)
            replays.setdefault(e["key"], {})[e["index"]] = e
    seen, versions = set(), {}
    for g in grades:
        if (g["family"], g["key"]) in seen:
            raise SystemExit(f"duplicate grade {g['family']} {g['key']}")
        seen.add((g["family"], g["key"]))
        row = by_key.get(g["key"])
        report_sha = hashlib.sha256(json.dumps(row.get("report"), sort_keys=True).encode()).hexdigest() if row else None
        if row is None or report_sha != g["report_sha256"] or g["row_runner_sha256"] != row.get("runner_sha256"):
            raise SystemExit(f"{g['family']} {g['key']}: grade does not match its row's report or runner")
        if whole_spec and g["spec_sha256"] != spec_sha:
            raise SystemExit(f"{g['family']} {g['key']}: grade under another spec")
        count = len((row.get("report") or {}).get("defects") or []) if isinstance(row.get("report"), dict) else 0
        mine = [replays.get(g["key"], {}).get(i) for i in range(count)]
        shown = hashlib.sha256(json.dumps(mine, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if None in mine or shown != g.get("replay_sha256"):
            raise SystemExit(f"{g['family']} {g['key']}: grade was made on another replay")
        for e in mine:  # every replay layer: spec, case, both builds, the row's runner, the replayer the grade names
            if ((whole_spec and e["spec_sha256"] != spec_sha) or e["case_digest"] != spec["case_digests"][row["id"]]
                    or e["case_build"] != spec["built_digests"][row["id"]] or e["clean_build"] != spec["oaw_src_digest"]
                    or e.get("row_runner_sha256") != row.get("runner_sha256")
                    or e["replayer_sha256"] != g.get("replayer_sha256") or e["report_sha256"] != report_sha):
                raise SystemExit(f"{g['family']} {g['key']}: replay entry does not match its row, spec or grade")
        if g.get("tool_calls", 0) != 0:
            raise SystemExit(f"{g['family']} {g['key']}: the grader used tools")
        versions.setdefault(g["family"], set()).add((g["grader_sha256"], g.get("replayer_sha256")))
    if any(len(v) > 1 for v in versions.values()):
        raise SystemExit("mixed grader or replayer versions")
    return {(g["family"], g["cell"], g["arm"], g["id"], g.get("rep", 1)): g for g in grades}


def inputs(a):
    """sha256 of every data file read, keyed by parent folder and name (both cells' files are named rows.jsonl)."""
    paths = a.rows.split(",") + a.grades.split(",") + a.replay.split(",") + ([a.controls] if getattr(a, "controls", None) else [])
    out = {}
    for p in paths:
        key = os.path.join(os.path.basename(os.path.dirname(os.path.abspath(p))), os.path.basename(p))
        if key in out:
            raise SystemExit(f"two inputs share the name {key}")
        out[key] = sha(p)
    return out


def calibrate(a, S, spec, spec_sha):
    rows, grades = read(a.rows), read(a.grades)
    graded = bind(spec, spec_sha, rows, grades, a.replay, whole_spec=False)
    defect = [j for j in spec["order"] if spec["kinds"][j] == "defect"]
    borrowed = json.load(open(a.borrowed, encoding="utf-8"))
    out = {"spec_sha256": spec_sha, "inputs": inputs(a),
           "borrowed": borrowed, "floors": {}, "ceiling": []}
    for cell in CELLS:
        for fam in FAMILIES:
            det, uns = {}, {}
            for j in defect:
                values = [graded.get((fam, cell, "N", j, rep)) for rep in (1, 2, 3)]
                if any(v is None for v in values):
                    raise SystemExit(f"calibration incomplete: {fam} {cell} {j}")
                det[j] = [v["detected"] for v in values]
                uns[j] = [v["unsupported"] for v in values]
            m_det, m_uns = S.pooled_within_sd(det), S.pooled_within_sd(uns)
            out["floors"].setdefault(cell, {})[fam] = {
                "measured": {"detection": m_det, "unsupported": m_uns},
                "borrowed": borrowed[fam],
                "detection": max(m_det, borrowed[fam]["detection"]),
                "unsupported": max(m_uns, borrowed[fam]["unsupported"])}
    for j in defect:
        if all(graded[(fam, cell, "N", j, rep)]["detected"] for fam in FAMILIES for cell in CELLS for rep in (1, 2, 3)):
            out["ceiling"].append(j)
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1)
    print("ceiling (replace before main):", out["ceiling"] or "none")
    print(json.dumps(out["floors"], indent=1))
    return 0


def judge(a, S, spec, spec_sha):
    controls = json.load(open(a.controls, encoding="utf-8"))
    if controls.get("spec_sha256") != spec_sha or not controls.get("pass"):
        raise SystemExit("the positive control did not pass for this spec (PREREG: the study stops)")
    rows, grades = read(a.rows), read(a.grades)
    graded = bind(spec, spec_sha, rows, grades, a.replay)
    for g in grades:  # the control must have vouched for the very grader and replayer versions used here
        if (g["grader_sha256"], g.get("replayer_sha256")) != tuple(controls["versions"].get(g["family"], (None, None))):
            raise SystemExit(f"{g['family']}: graded with a version the positive control did not check")
    floor = json.load(open(a.floor, encoding="utf-8"))
    # Replacement history lives in the frozen spec (built before the main runs): {old journey: its replacement}.
    replaced = spec.get("ceiling_replaced") or {}
    if (set(replaced) & set(spec["order"]) or not set(replaced.values()) <= set(spec["order"])
            or set(replaced) & set(replaced.values()) or len(set(replaced.values())) != len(replaced)):
        raise SystemExit("ceiling_replaced is not a single round of replacements inside the frozen order")
    if replaced and not (spec.get("ceiling_provenance") or {}).get("prior_floor_sha256"):
        raise SystemExit("replacements without the prior calibration they came from")
    kept = set(replaced.values())  # a replacement still at the ceiling is kept and flagged (replaced once only)
    if floor["spec_sha256"] != spec_sha or set(floor["ceiling"]) - kept:
        raise SystemExit("floor file is for another spec, or ceiling journeys were not replaced")
    journeys = list(spec["order"])
    defect = [j for j in journeys if spec["kinds"][j] == "defect"]
    critical = [j for j in defect if spec["truth"][j]["severity"] == "critical"]
    by_row = {(r["cell"], r["arm"], r["id"]): r for r in rows if r.get("rep", 1) == 1}
    result = {"spec_sha256": spec_sha, "inputs": inputs(a), "floor_sha256": sha(a.floor), "eval_stats_sha256": sha(a.eval_stats),
              "ceiling_flagged": sorted(set(floor["ceiling"]) & kept), "cells": {}}
    for cell in CELLS:
        missing = [(arm, j, fam) for arm in ("N", "C", "D", "F") for j in journeys for fam in FAMILIES
                   if (cell, arm, j) not in by_row or (fam, cell, arm, j, 1) not in graded]
        if missing:
            result["cells"][cell] = {"outcome": None, "reason": f"incomplete: {missing[:5]}"}
            continue

        def metric(fam, arm, name, ids):
            return {j: [graded[(fam, cell, arm, j, 1)][name]] for j in ids}

        doc = {"comparisons": {}}
        for arm in ("F", "C", "D"):  # F decides; C and D are described with the same yardstick
            comp = {}
            for fam in FAMILIES:
                fl = floor["floors"][cell][fam]
                det = S.compare(metric(fam, arm, "detected", defect), metric(fam, "N", "detected", defect), 0.10,
                                floor_sd=fl["detection"])
                uns = S.compare(metric(fam, arm, "unsupported", journeys), metric(fam, "N", "unsupported", journeys), 0.5,
                                lower_is_better=True, floor_sd=fl["unsupported"])
                comp[fam] = {"detection": {k: det[k] for k in ("point", "ci95", "ci90", "class", "floor_applied")},
                             "unsupported": {k: uns[k] for k in ("point", "ci95", "ci90", "class", "floor_applied")},
                             "quality": S.quality(det["class"], uns["class"]),
                             "detected": sum(v[0] for v in metric(fam, arm, "detected", defect).values()),
                             "native_detected": sum(v[0] for v in metric(fam, "N", "detected", defect).values())}
            comp["quality"] = S.agree(comp["opus"]["quality"], comp["codex"]["quality"])
            comp["missed_critical"] = [j for j in critical
                                       if not all(graded[(fam, cell, arm, j, 1)]["detected"] for fam in FAMILIES)]
            if comp["quality"] == "better" and comp["missed_critical"]:
                comp["quality"], comp["downgraded"] = "undetermined", "missed a planted critical defect (BASH rule)"
            tokens = {j: [by_row[(cell, arm, j)]["tokens_total"]] for j in journeys}
            native = {j: [by_row[(cell, "N", j)]["tokens_total"]] for j in journeys}
            comp["cost"] = {k: v for k, v in S.cost(tokens, native).items() if k != "per_question"}
            comp["bash_pass"] = (all(comp[f]["detection"]["class"] == "better" for f in FAMILIES)
                                 and all(comp[f]["unsupported"]["ci95"][1] < 0.5 for f in FAMILIES)
                                 and not comp["missed_critical"] and comp["cost"]["ci95"][1] <= 1.5)
            q, c = comp["quality"], comp["cost"]["class"]
            if q == "worse":
                outcome = "excrete"
            elif q == "better":
                outcome = "optional" if c == "over" or not comp["bash_pass"] else "default"
            elif q == "equivalent":
                outcome = ("default" if c == "cheaper" and comp["bash_pass"] else "excrete" if c == "over" else "optional")
            else:
                outcome = "excrete" if c == "over" else "optional"
            comp["outcome"] = outcome
            doc["comparisons"][arm] = comp
        doc["outcome"] = doc["comparisons"]["F"]["outcome"]
        doc["tokens_median"] = {arm: statistics.median(by_row[(cell, arm, j)]["tokens_total"] for j in journeys)
                                for arm in ("N", "C", "D", "F")}
        # Pre-registered reading of the cheap method: if C passes BASH too and F is not better than C in detection for
        # both families, the hint line alone carries the gain (reported for the owner, not a verdict on F).
        fc = {fam: S.compare(metric(fam, "F", "detected", defect), metric(fam, "C", "detected", defect), 0.10,
                             floor_sd=floor["floors"][cell][fam]["detection"])["class"] for fam in FAMILIES}
        doc["F_vs_C_detection"] = fc
        doc["hint_suffices"] = bool(doc["comparisons"]["C"]["bash_pass"] and all(v != "better" for v in fc.values()))
        result["cells"][cell] = doc
    outcomes = [result["cells"][c].get("outcome") for c in CELLS]
    result["outcome"] = None if None in outcomes else min(outcomes, key=OUTCOME_ORDER.index)
    result["bash_pass"] = None if None in outcomes else all(
        result["cells"][c]["comparisons"]["F"]["bash_pass"] for c in CELLS)
    result["quality_lowest"] = (None if None in outcomes else
                                S.lowest(*[result["cells"][c]["comparisons"]["F"]["quality"] for c in CELLS]))
    json.dump(result, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for cell in CELLS:
        d = result["cells"][cell]
        f = d.get("comparisons", {}).get("F", {})
        print(cell, "F:", f.get("quality"), f.get("cost", {}).get("ratio"), f.get("cost", {}).get("class"),
              "BASH", f.get("bash_pass"), "->", d.get("outcome"))
    print("I16 outcome (lowest cell):", result["outcome"])
    return 0


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("step", choices=("calibrate", "judge"))
    p.add_argument("--eval-stats", required=True)
    p.add_argument("--cases", required=True)
    p.add_argument("--rows", required=True)
    p.add_argument("--grades", required=True)
    p.add_argument("--replay", required=True, help="the replay file(s) the grades were made on")
    p.add_argument("--borrowed")
    p.add_argument("--floor")
    p.add_argument("--controls", help="controls.json from i16_controls.py check (judge step)")
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    S = load_stats(a.eval_stats)
    spec_path = os.path.join(a.cases, "spec.json")
    spec = json.load(open(spec_path, encoding="utf-8"))
    return (calibrate if a.step == "calibrate" else judge)(a, S, spec, sha(spec_path))


if __name__ == "__main__":
    sys.exit(main())
