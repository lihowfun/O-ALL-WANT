#!/usr/bin/env python3
"""Synthetic dry check of the ledger, binding, freeze, budget and gate paths of h1_run.py (version 3, no model calls).
    python3 freeze_check.py <H1 folder> <OAW checkout> <empty state folder>"""
import argparse
import fcntl
import json
import os
import shutil
import sys

h1, oaw_src, state = sys.argv[1], sys.argv[2], sys.argv[3]
if os.listdir(state):
    raise SystemExit("give an empty state folder")
oaw = os.path.join(state, "oaw")
os.makedirs(os.path.join(oaw, "scripts"))
for name in ("oaw_mode.py", "eval_stats.py"):
    shutil.copyfile(os.path.join(oaw_src, "scripts", name), os.path.join(oaw, "scripts", name))
os.environ.update({"H1_STATE": state, "H1_BASE": state, "H1_OAW": oaw, "H1_HIDE": "/nonexistent", "H1_BIN": "/usr/bin",
                   "H1_RO": "/usr"})
sys.path.insert(0, h1)
sys.dont_write_bytecode = True
import h1_run as R  # noqa: E402

os.makedirs(os.path.join(state, "arms"))
json.dump({"exit": 0, "cases": {"tests.t::test_x": "passed"}}, open(R.baseline_path(), "w"))
ok = bad = 0


def check(name, good, detail=""):
    global ok, bad
    ok, bad = ok + bool(good), bad + (not good)
    print("ok  " if good else "FAIL", name, "" if good else detail)


def refused(fn, *args, contains=""):
    try:
        fn(*args)
    except SystemExit as error:
        return contains in str(error) or str(error)
    return False


def unit(uid, kind):
    return {"id": uid, "type": kind, "sessions": ["p1", "p2"], "facts": ["X_1"], "hidden_test": "def test_a(): pass",
            "reference_patch": "diff", "junk_field": "must not be copied"}


def author(klass, name, units, supplies=None, not_run="", interrupted=False, brief=None):
    """A ledger start entry, the candidates file and an end entry, as cmd_author leaves them."""
    R.append(R.authors_path(), {"event": "start", "klass": klass, "name": name, "supplies": supplies,
                                "brief_sha256": brief or R.digest(R.brief_path(klass)), "runner_sha256": R.runner_digest()})
    if interrupted:
        return
    path = R.candidates_path(name, klass)
    json.dump({"units": units}, open(path, "w"))
    R.append(R.authors_path(), {"event": "end", "klass": klass, "name": name, "not_run": not_run,
                                "files": {f"units_{klass}.json": {"sha256": R.digest(path), "units": [u["id"] for u in units]}}})


def verify(klass, name, units, invalid=(), **override):
    report = {"klass": klass, "author": name, "candidates_sha256": R.digest(R.candidates_path(name, klass)),
              "runner_sha256": R.runner_digest(), "baseline_sha256": R.digest(R.baseline_path()),
              "oaw_mode_sha256": R.digest(os.path.join(oaw, "scripts", "oaw_mode.py")),
              "units": [{"id": u["id"], "type": u["type"], "valid": u["id"] not in invalid,
                         "checks": {"c1": u["id"] not in invalid, "c2": True}, "functions": ["test_a"],
                         "nodes": {"test_a": ["test_a"]}, "items": {"test_a": ["test_a"]}, "reference_lines": 5,
                         "sha256": R.unit_digest(u)} for u in units]}
    report.update(override)
    json.dump(report, open(R.verified_path(name, klass), "w"))
    return {u["id"]: u for u in report["units"]}


def counted_row(tag, unit_id, score, extra, started=None):
    row = dict({"unit": unit_id, "arm": "N1", "attempt": 1, "started": started or f"{tag}-{unit_id}", "score": score},
               **extra)
    R.append(os.path.join(state, f"rows-{tag}-codex.jsonl"), row)
    R.append(os.path.join(state, f"attempts-{tag}-codex.jsonl"), row)


def freeze(**kw):
    base = dict(klass="B", candidates=None, verified=None, ids="", stage="final")
    base.update(kw)
    try:
        return R.cmd_freeze(argparse.Namespace(**base)), None
    except SystemExit as error:
        return None, str(error)


def frozen(name):
    return json.load(open(os.path.join(state, name), encoding="utf-8"))


def reset(*names):
    for name in names:
        path = os.path.join(state, name)
        if os.path.exists(path):
            os.remove(path)


# ---- class B: first author
kinds = ("explicit", "passing", "superseded", "handoff")
b1 = [unit(f"{k}-{i}-a1", k) for k in kinds for i in (1, 2)]
author("B", "a1", b1)
rep1 = verify("B", "a1", b1, invalid={"superseded-1-a1"})
v1 = R.verified_path("a1", "B")
for uid, score in (("explicit-1-a1", 0.5), ("explicit-2-a1", 1.0), ("passing-1-a1", 1.0), ("passing-2-a1", 1.0),
                   ("superseded-2-a1", 0.5), ("handoff-1-a1", 1.0), ("handoff-2-a1", 1.0)):
    counted_row("solver", uid, score, R.bound_to(rep1[uid], v1))
code, err = freeze()
check("B: a short type returns 7 and writes nothing", code == 7 and not os.path.exists(os.path.join(state, "units_B.json")))
missing = json.load(open(R.missing_path("B")))
check("B: missing-B.json names the type and the authors so far (#2)", missing == {"types": ["superseded"], "after_authors": ["a1"]})
check("B: files given to a class B freeze are refused", "from the author ledger" in (freeze(candidates="x")[1] or ""))

# cmd_author refusals happen before any session
def run_author(name, klass="B"):
    return R.cmd_author(argparse.Namespace(klass=klass, name=name, hours=1))

check("author: a used name is refused (#2)", refused(run_author, "a1", contains="already ran") is True)
os.rename(R.missing_path("B"), R.missing_path("B") + ".bak")
check("author: a supplement without missing-B.json is refused (#2)", refused(run_author, "a2", contains="missing types first") is True)
json.dump({"types": ["superseded"], "after_authors": []}, open(R.missing_path("B"), "w"))
check("author: missing-B.json written before the last author is refused (#2)", refused(run_author, "a2", contains="run freeze again") is True)
os.replace(R.missing_path("B") + ".bak", R.missing_path("B"))

# a supplement that ended as not run does not count; a supplement supplies only its types
author("B", "x1", [unit("superseded-9-x1", "superseded")], supplies=["superseded"], not_run="usage limit")
check("ledger: a not-run author does not count", [n for n, _s, _e in R.counted_authors("B")] == ["a1"])
b2 = [unit(f"superseded-{i}-a2", "superseded") for i in (1, 2)] + [unit("explicit-1-a2", "explicit")]
author("B", "a2", b2, supplies=["superseded"])
rep2 = verify("B", "a2", [u for u in b2 if u["type"] == "superseded"])
v2 = R.verified_path("a2", "B")
counted_row("solver", "superseded-2-a2", 1.0, R.bound_to(rep2["superseded-2-a2"], v2))
code, err = freeze()
check("B: superseded-1-a2 has no solver row, so the freeze stops", code is None and "superseded-1-a2 has no solver result" in err, err)
counted_row("solver", "superseded-1-a2", 0.75, R.bound_to(rep2["superseded-1-a2"], v2))
code, err = freeze()
out = frozen("units_B.json") if code == 0 else {"units": [], "notes": {}, "sources": [], "inputs": {}}
ids = [u["id"] for u in out["units"]]
check("B: one per type in authoring order; the supplement fills only its type (#2)",
      ids == ["explicit-2-a1", "passing-1-a1", "handoff-1-a1", "superseded-2-a2"], (code, err, ids))
check("B: the supplement's explicit unit is not considered", "explicit-1-a2" not in out["notes"])
check("B: carry is repo for handoff only", [u["carry"] for u in out["units"]] == ["home", "home", "repo", "home"])
check("B: notes", out["notes"].get("explicit-1-a1") == "dropped: full-memory solver scored 0.5"
      and out["notes"].get("superseded-1-a1") == "dropped: failed c1" and out["notes"].get("passing-2-a1") == "valid, spare")
check("B: entries carry nodes and the candidate digest; unknown fields are not copied (#3, #5)",
      all(u["nodes"] == {"test_a": ["test_a"]} and u["candidate_sha256"] == R.unit_digest(next(c for c in b1 + b2 if c["id"] == u["id"]))
          and "junk_field" not in u and "cases" not in u for u in out["units"]))
check("B: sources per counted author with supplies and digests (#2)",
      [(s["name"], s["supplies"]) for s in out["sources"]] == [("a1", None), ("a2", ["superseded"])]
      and all(s["brief_sha256"] == R.digest(R.brief_path("B")) for s in out["sources"]))
check("B: missing-B.json removed after a complete freeze", not os.path.exists(R.missing_path("B")))
check("B: the solver rows' digest is in the unit file", out["inputs"] == {"solver_sha256": R.digest(os.path.join(state, "rows-solver-codex.jsonl"))})

# binding (#3)
rows_path = os.path.join(state, "rows-solver-codex.jsonl")
saved = open(rows_path).read()
first = json.loads(saved.splitlines()[1])
open(rows_path, "w").write(saved + json.dumps(dict(first, started="again")) + "\n")
code, err = freeze()
check("B: two counted solver rows of a unit are refused (#2)", code is None and "two counted rows" in err, err)
open(rows_path, "w").write(saved.replace(first["verified_sha256"], "0" * 64, 1))
code, err = freeze()
check("B: a solver row bound to another verification report is refused (#3)", code is None and "another verified_sha256" in err, err)
open(rows_path, "w").write(saved.replace('"attempt": 1', '"attempt": 2', 1))
code, err = freeze()
check("B: a solver row the attempts file does not hold is refused", code is None and "not in the attempts file" in err, err)
open(rows_path, "w").write(saved)
original = open(R.candidates_path("a1", "B")).read()
open(R.candidates_path("a1", "B"), "w").write(original.replace("p1", "p9", 1))
code, err = freeze()
check("B: candidates changed after the author run are refused (#2)", code is None and "changed after the author run" in err, err)
open(R.candidates_path("a1", "B"), "w").write(original)
verify("B", "a1", b1, invalid={"superseded-1-a1"}, runner_sha256="x")
code, err = freeze()
check("B: a report made by another runner is refused (#3)", code is None and "runner_sha256" in err, err)
rep1 = verify("B", "a1", b1, invalid={"superseded-1-a1"})
code, err = freeze()
check("B: the freeze is reproducible with the same inputs", code == 0 and [u["id"] for u in frozen("units_B.json")["units"]] == ids)
check("solver: every valid unit already has its bound result, so nothing runs", R.cmd_solver(argparse.Namespace(author="a1")) == 0)
open(rows_path, "w").write(saved.replace(first["runner_sha256"], "1" * 64, 1))
check("solver: a stored result of another runner stops the solver before any session (#3)",
      refused(R.cmd_solver, argparse.Namespace(author="a1"), contains="another runner_sha256") is True)
open(rows_path, "w").write(saved)

# a third counted author is the last; a fourth is refused
author("B", "a3", [unit("handoff-3-a3", "handoff")], supplies=["handoff"], interrupted=True)
check("ledger: an interrupted author counts", [n for n, _s, _e in R.counted_authors("B")] == ["a1", "a2", "a3"])
check("author: more than MAX_AUTHORS counted runs is refused (#2)", refused(run_author, "a4", contains="stop and report") is True)

# ---- class C
cu = [unit(f"large-{i}-c1", "large") for i in (1, 2, 3, 4)] + [unit(f"design-{i}-c1", "design") for i in (1, 2, 3)]
author("C", "c1", cu)
repc = verify("C", "c1", cu, invalid={"design-2-c1"})
vc = R.verified_path("C".lower() + "1", "C")
code, err = freeze(klass="C", stage="calibration")
check("C: an unaudited usable unit stops", code is None and err.endswith("has not been audited"), err)
audit = {}
for u in cu:
    if u["id"] == "design-2-c1":
        continue
    audit[u["id"]] = dict(R.bound_to(repc[u["id"]], vc), attempts=[], invalid=False,
                          result={"struck": ["test_a"] if u["id"] == "large-1-c1" else [], "answer": {}})
audit["design-3-c1"].update(result=None, invalid=True)
json.dump(audit, open(os.path.join(state, "audit-C.json"), "w"))
code, err = freeze(klass="C", stage="calibration")
cal = frozen("units_C_calibration.json") if code == 0 else {"units": [], "notes": {}}
check("C calibration: usable units the audit left, authoring order", [u["id"] for u in cal["units"]] ==
      ["large-2-c1", "large-3-c1", "large-4-c1", "design-1-c1"], (code, err))
check("C calibration: struck and schema-invalid units noted (#11)",
      cal["notes"].get("large-1-c1") == "dropped: the audit struck test_a"
      and cal["notes"].get("design-3-c1") == "dropped: the audit replies broke the schema")
audit["large-2-c1"]["verified_sha256"] = "0" * 64
json.dump(audit, open(os.path.join(state, "audit-C.json"), "w"))
code, err = freeze(klass="C", stage="calibration")
check("C: an audit bound to another verification report is refused (#3)", code is None and "another verified_sha256" in err, err)
audit["large-2-c1"]["verified_sha256"] = R.digest(vc)
json.dump(audit, open(os.path.join(state, "audit-C.json"), "w"))
freeze(klass="C", stage="calibration")
entries = {u["id"]: R.unit_digest(u) for u in frozen("units_C_calibration.json")["units"]}
runner = R.runner_digest()
code, err = freeze(klass="C")
check("C final: a pool unit without a calibration run stops", code is None and "has no calibration run" in err, err)
for uid, score in (("large-2-c1", 1.0), ("large-3-c1", 0.5), ("large-4-c1", 0.75), ("design-1-c1", 0.25)):
    counted_row("calibration", uid, score, {"unit_sha256": entries[uid], "runner_sha256": runner})
code, err = freeze(klass="C")
check("C final: a short type returns 7 and names it (#2)", code == 7 and json.load(open(R.missing_path("C")))["types"] == ["design"], (code, err))
reset("rows-calibration-codex.jsonl", "attempts-calibration-codex.jsonl")
counted_row("calibration", "large-2-c1", 1.0, {"unit_sha256": "0" * 64, "runner_sha256": runner})
code, err = freeze(klass="C")
check("C final: a calibration run of another unit entry is refused (#3)", code is None and "another unit entry" in err, err)
reset("rows-calibration-codex.jsonl", "attempts-calibration-codex.jsonl")
# supplement for design
cu2 = [unit(f"design-{i}-c2", "design") for i in (1, 2)] + [unit("large-9-c2", "large")]
author("C", "c2", cu2, supplies=["design"])
repc2 = verify("C", "c2", [u for u in cu2 if u["type"] == "design"])
vc2 = R.verified_path("c2", "C")
for u in cu2[:2]:
    audit[u["id"]] = dict(R.bound_to(repc2[u["id"]], vc2), attempts=[], invalid=False, result={"struck": [], "answer": {}})
json.dump(audit, open(os.path.join(state, "audit-C.json"), "w"))
code, err = freeze(klass="C", stage="calibration")
entries = {u["id"]: R.unit_digest(u) for u in frozen("units_C_calibration.json")["units"]}
check("C calibration after a supplement keeps earlier entries unchanged (#3)",
      code == 0 and "large-9-c2" not in entries and len(entries) == 6, (code, err, sorted(entries)))
for uid, score in (("large-2-c1", 1.0), ("large-3-c1", 0.5), ("large-4-c1", 0.75), ("design-1-c1", 0.25),
                   ("design-1-c2", 1.0), ("design-2-c2", 0.0)):
    counted_row("calibration", uid, score, {"unit_sha256": entries[uid], "runner_sha256": runner})
code, err = freeze(klass="C")
out = frozen("units_C.json") if code == 0 else {"units": [], "notes": {}}
check("C final: per type the first two below ceiling in authoring order, no ceiling fill",
      [u["id"] for u in out["units"]] == ["large-3-c1", "large-4-c1", "design-1-c1", "design-2-c2"], (code, err))
check("C final: ceiling units dropped", out["notes"].get("large-2-c1") == "calibration 1.0, dropped: at ceiling"
      and out["notes"].get("design-1-c2") == "calibration 1.0, dropped: at ceiling")
check("C final: inputs carry audit and calibration digests", sorted(out.get("inputs", {})) == ["audit_sha256", "calibration_sha256"])
check("audit: every valid unit already has its bound audit, so nothing runs", R.cmd_audit(argparse.Namespace(author="c1")) == 0)
audit["large-3-c1"]["candidate_sha256"] = "2" * 64
json.dump(audit, open(os.path.join(state, "audit-C.json"), "w"))
check("audit: a stored audit of another candidate stops the audit before any session (#3)",
      refused(R.cmd_audit, argparse.Namespace(author="c1"), contains="another candidate_sha256") is True)
audit["large-3-c1"]["candidate_sha256"] = repc["large-3-c1"]["sha256"]
json.dump(audit, open(os.path.join(state, "audit-C.json"), "w"))

# ---- budget, ledger, lock and gate (#6, #12)
check("budget: nothing runs before the base is written", refused(R.budget, contains="no budget base") is True)
R.cmd_budget(argparse.Namespace(spent_before=1_400_000, raise_to=None, decision=None))
check("budget: the base is written once", refused(R.cmd_budget, argparse.Namespace(spent_before=0, raise_to=None, decision=None), contains="written once") is True)
check("budget: base read back", R.budget() == (30_000_000, "D35", 1_400_000))
check("budget: a raise must name a decision", refused(R.cmd_budget, argparse.Namespace(spent_before=None, raise_to=40_000_000, decision="ok"), contains="owner decision") is True)
check("budget: a raise must raise", refused(R.cmd_budget, argparse.Namespace(spent_before=None, raise_to=20_000_000, decision="D40"), contains="larger") is True)
R.append(R.ledger_path(), {"event": "start", "key": "k1", "raw": "raw1.jsonl", "reserve": 500_000})
R.append(R.ledger_path(), {"event": "end", "key": "k1", "tokens": 300_000})
R.append(R.ledger_path(), {"event": "start", "key": "k2", "raw": "raw2.jsonl", "reserve": 200_000})
check("ledger: an interrupted session is held at its reserve", R.cell_spent() == 1_400_000 + 300_000 + 200_000, R.cell_spent())
open(os.path.join(state, "raw2.jsonl"), "w").write(
    json.dumps({"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 100_000, "cache_read_input_tokens": 400_000}}}) + "\n"
    + json.dumps({"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 100_000, "cache_read_input_tokens": 400_000}}}) + "\n")
check("ledger: or at the usage its raw file shows, when larger (#6)", R.cell_spent() == 1_400_000 + 300_000 + 500_000, R.cell_spent())
lock = R.claude_lock()
check("lock: a second claude-cell run is refused (#6)", refused(R.claude_lock, contains="holds the lock") is True)
del lock
gate = R.gate()
check("gate: incomplete inputs are not stored", gate["open"] is False and not os.path.exists(os.path.join(state, "gate-C.json")))
json.dump({"open": True, "raises": 0, "cap": 30_000_000}, open(os.path.join(state, "gate-C.json"), "w"))
check("gate: an open decision is reused on resume (#12)", R.gate()["stored"] is True and R.gate()["open"] is True)
json.dump({"open": False, "raises": 0, "cap": 30_000_000}, open(os.path.join(state, "gate-C.json"), "w"))
check("gate: a closed decision stays closed without a raise (#12)", R.gate()["stored"] is True and R.gate()["open"] is False)
R.cmd_budget(argparse.Namespace(spent_before=None, raise_to=40_000_000, decision="D40"))
check("budget: a recorded raise moves the cap", R.budget()[:2] == (40_000_000, "D40"))
check("gate: a closed decision is decided again after a raise (#12)", R.gate()["stored"] is False)

# ---- an attempt that was started and never finished counts (no free reruns by stopping the runner)
R.append(R.starts_path("pilot", "codex"), {"unit": "u1", "arm": "O", "attempt": 1, "root": "runs/main/codex/u1/O/a1"})
R.append(R.starts_path("pilot", "codex"), {"unit": "u1", "arm": "O", "attempt": 2, "root": "runs/main/codex/u1/O/a2"})
R.append(os.path.join(state, "attempts-pilot-codex.jsonl"), {"unit": "u1", "arm": "O", "attempt": 2,
                                                           "root": "runs/main/codex/u1/O/a2", "not_run": ""})
seen = R.tried("pilot", "codex", "u1", "O")
check("attempts: a start without a finished attempt counts as interrupted",
      sorted((r["attempt"], r.get("not_run")) for r in seen) == [(1, "interrupted"), (2, "")], seen)
check("attempts: other arms are not mixed in", R.tried("pilot", "codex", "u1", "N1") == [])
check("class A ids are the pre-registered ones", "class A is t01,t04,t09,t12" in (freeze(klass="A", candidates="c", verified="v", ids="t01,t02,t09,t12")[1] or ""))

# ---- round 3: counted attempts reconcile with rows, recovery, locks, the class A bank, bound interrupted starts
reset("rows-calibration-codex.jsonl", "attempts-calibration-codex.jsonl")
R.append(os.path.join(state, "attempts-calibration-codex.jsonl"), {"unit": "z1", "arm": "N1", "attempt": 1, "started": "t1", "root": "r1", "score": 1.0})
R.append(os.path.join(state, "attempts-calibration-codex.jsonl"), {"unit": "z1", "arm": "N1", "attempt": 2, "started": "t2", "root": "r2", "score": 0.5})
R.append(os.path.join(state, "rows-calibration-codex.jsonl"), {"unit": "z1", "arm": "N1", "attempt": 2, "started": "t2", "root": "r2", "score": 0.5})
check("calibration: two counted attempts of one unit are refused (round 3 #2)", refused(R.counted_rows, "calibration", contains="two counted attempts") is True)
reset("rows-calibration-codex.jsonl", "attempts-calibration-codex.jsonl")
R.append(os.path.join(state, "attempts-calibration-codex.jsonl"), {"unit": "z1", "arm": "N1", "attempt": 1, "started": "t1", "root": "r1", "score": 1.0})
check("a counted attempt without its row is refused by the freeze (round 3 #2)", refused(R.counted_rows, "calibration", contains="without a row") is True)
R.recover("calibration", "codex")
check("recover writes the missing row, so the run is not repeated (round 3 #2)",
      [r["root"] for r in R.read_rows(os.path.join(state, "rows-calibration-codex.jsonl"))] == ["r1"] and R.counted_rows("calibration")["z1"]["score"] == 1.0)
reset("rows-calibration-codex.jsonl", "attempts-calibration-codex.jsonl")
bound = {"candidate_sha256": "c", "verified_sha256": "v", "runner_sha256": R.runner_digest()}
R.append(R.starts_path("solver", "codex"), dict(bound, tag="solver", cell="codex", klass="B", unit="u9", arm="N1", attempt=1, root="runs/solver/codex/u9/N1/a1"))
lost = R.tried("solver", "codex", "u9")
check("an interrupted solver start carries its binding, so the solver can resume (round 3 #10)",
      len(lost) == 1 and lost[0]["not_run"] == "interrupted" and R.refuse_other(lost[0], bound, "x") is None)
check("class A from another bank is refused (round 3 #4)", "frozen tokeneconomizer bank" in (freeze(klass="A", candidates=R.candidates_path("a1", "B"), verified="v", ids="t01,t04,t09,t12")[1] or ""))
R.append(R.starts_path("main", "codex"), {"tag": "main", "unit": "x", "arm": "N1", "attempt": 1, "root": "runs/main/codex/x/N1/a1"})
code, err = freeze()
check("a main start alone locks the unit files (round 3 #4)", code is None and "main runs have started" in err, err)
check("and the freeze file (round 3 #4)", refused(R.cmd_manifest, argparse.Namespace(write=True, out=os.path.join(state, "F.json")), contains="main runs have started") is True)

# ---- frozen once main rows exist
R.append(os.path.join(state, "rows-main-codex.jsonl"), {"unit": "x"})
code, err = freeze()
check("final freeze refused once main rows exist", code is None and "main runs have started" in err)
code, err = freeze(klass="C", stage="calibration")
check("calibration-stage file can still be written", code == 0)

print(f"{ok} passed, {bad} failed")
sys.exit(1 if bad else 0)
