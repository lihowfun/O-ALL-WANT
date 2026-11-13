#!/usr/bin/env python3
"""One offline recovery for FIXCHECK passing-1-b1; never invokes a model."""
import argparse
from collections import Counter
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
UNIT = "passing-1-b1"
ROOT = "runs/fixcheck/codex/passing-1-b1/O/a1"


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fx, calc = load("fixcheck"), load("thresholds")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n")


def rows(path):
    p = Path(path)
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()] if p.exists() else []


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def original_inputs(state):
    index = read(state / "RECOVERY_INPUTS.json")
    for name, expected in index["files"].items():
        p = state / name
        if p.stat().st_size != expected["size"] or sha(p) != expected["sha256"]:
            raise ValueError("original recovery input changed: " + name)
    return sha(state / "RECOVERY_INPUTS.json")


def session(runner, root, number, allow_truncated=False):
    raw = root / "raw" / f"s{number}.jsonl"
    events = [json.loads(line) for line in raw.read_text().splitlines()]
    ids = [e["thread_id"] for e in events if e["type"] == "thread.started"]
    turns = [e for e in events if e["type"] == "turn.completed"]
    if len(ids) != 1 or len(turns) != 1 or events[-1]["type"] != "turn.completed":
        raise ValueError("not a complete single parent turn")
    items = [e["item"] for e in events if e["type"] == "item.completed"]
    allowed = {"agent_message", "command_execution", "file_change", "reasoning", "error"}
    if {i["type"] for i in items} - allowed:
        raise ValueError("unknown tool type; cannot exclude child activity")
    if any(e["type"] in ("error", "turn.failed") for e in events):
        raise ValueError("failed parent turn")
    errors = [i for i in items if i["type"] == "error"]
    if errors and not (allow_truncated and len(errors) == 1
                       and "No space left on device" in errors[0].get("message", "")):
        raise ValueError("unexplained stream error")
    copies = list((root / "raw" / f"s{number}-rollouts").glob("*.jsonl"))
    if len(copies) != 1:
        raise ValueError("child or missing rollout")
    rollout = copies[0]
    home_matches = list((root / "home/.codex/sessions").rglob(rollout.name))
    if len(home_matches) != 1 or sha(home_matches[0]) != sha(rollout):
        raise ValueError("rollout copy differs from original home")
    lines = rollout.read_text().splitlines()
    malformed = []
    for n, line in enumerate(lines, 1):
        try:
            json.loads(line)
        except ValueError:
            malformed.append(n)
    if malformed != ([len(lines)] if allow_truncated else []):
        raise ValueError("unexpected rollout truncation")
    facts = runner.rollout_facts(str(rollout))
    if (facts["thread"] != ids[0] or facts["provider"] != "openai"
            or facts["model_missing"] or set(facts["models"]) != {"gpt-6.1-sol"}):
        raise ValueError("root identity not established")
    if any("collaboration." in text for text in facts["tool_texts"]):
        raise ValueError("possible child activity requires separate audit")
    if facts["context"].get("effort") != "high":
        raise ValueError("unexpected effort")
    usage = turns[0]["usage"]
    total = usage["input_tokens"] + usage["output_tokens"]
    noncache = total - usage["cached_input_tokens"]
    old_total, old_noncache = runner.rollout_tokens(str(rollout))
    if not allow_truncated and (total, noncache) != (old_total, old_noncache):
        raise ValueError("complete stream/rollout usage disagree")
    if allow_truncated and not (0 < old_total < total):
        raise ValueError("truncation does not explain the usage gap")
    finals = [i.get("text", "") for i in items if i["type"] == "agent_message" and i.get("text", "").strip()]
    saved = (root / "raw" / f"s{number}.final.txt").read_text().split("\n---\n", 1)
    if not finals or finals[-1] != saved[0]:
        raise ValueError("final answer differs from saved answer")
    result = {
        "exit": None, "seconds": None, "api_key_source": None,
        "tools": dict(Counter(i["type"] for i in items if i["type"] not in ("agent_message", "reasoning"))),
        "skills": facts["skill_reads"], "agents": 0, "threads": 1, "evidence": {},
        "blocked": facts["blocked"], "provider": facts["provider"],
        "root_models": sorted(set(facts["models"])), "root_model_missing": False,
        "model": "gpt-6.1-sol", "models_used": ["gpt-6.1-sol"],
        "context": facts["context"], "listed_skills": facts["listed_skills"],
        "listed_tools": facts["listed_tools"], "result_seen": True,
        "errors": [], "is_error": False, "limit_seen": None, "over_ceiling": False,
        "tokens_total": total, "tokens_noncache": noncache,
        "tokens_from": "complete parent stream; no child threads",
        "memory_files": None, "changed": None, "fact_places": None,
        "recovery": {
            "original_not_run_gate": "accepted before the observed grade-stage exception",
            "missing_measurements": ["process exit", "wall seconds", "billing-source measurement",
                                     "limit_seen measurement", "intermediate memory/changed/fact snapshots"],
            "stream_sha256": sha(raw), "rollout_sha256": sha(rollout),
            "rollout_logical_tokens": old_total, "stream_logical_tokens": total,
            "malformed_rollout_lines": malformed,
            "stream_error_items": errors,
        },
    }
    for text in facts["tool_texts"]:
        runner.evidence(result, text)
    return result


def append_once(attempt_path, row_path, row):
    key = lambda r: (r["cell"], r["unit"], r["arm"])
    present = []
    for path in (attempt_path, row_path):
        existing = rows(path)
        hits = [r for r in existing if r.get("root") == row["root"] or key(r) == key(row)]
        if len(hits) > 1 or any(canonical(r) != canonical(row) for r in hits):
            raise ValueError("conflicting recovery row")
        present.append(bool(hits))
    if present[1] and not present[0]:
        raise ValueError("counted row without attempt")
    for path, already in zip((attempt_path, row_path), present):
        if not already:
            with Path(path).open("a") as handle:
                handle.write(canonical(row) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
    return present


def selftest():
    row = {"cell": "codex", "unit": UNIT, "arm": "O", "root": ROOT}
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "attempts", Path(tmp) / "rows"
        append_once(a, b, row)
        first = (a.read_bytes(), b.read_bytes())
        append_once(a, b, row)
        assert first == (a.read_bytes(), b.read_bytes())
        b.unlink()
        append_once(a, b, row)
        assert first == (a.read_bytes(), b.read_bytes())
        conflict = dict(row, root=ROOT + "-another")
        try:
            append_once(a, b, conflict)
        except ValueError:
            pass
        else:
            raise AssertionError("conflict accepted")
        assert first == (a.read_bytes(), b.read_bytes())
    print("3 ledger recovery checks passed; no experiment ledger touched.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "append", "selftest"))
    args = parser.parse_args()
    if args.action == "selftest":
        selftest()
        return
    runner, freeze = fx.load_runner()
    state = Path(runner.STATE)
    with (state / "fixcheck.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = fx.check(runner, freeze, pushed=True)
        proposed = state / "PROPOSED_RECOVERY_ROW.json"
        if args.action == "append":
            row = read(proposed)
            approval = read(state / "RECOVERY_REVIEW.json")
            if (approval.get("verdict") != "PASS" or approval.get("row_sha256") != sha(proposed)
                    or approval.get("script_sha256") != sha(__file__)
                    or approval.get("manifest_sha256") != sha(fx.MANIFEST)):
                raise ValueError("missing matching independent recovery review")
            unit_meta = next(u for u in manifest["units"] if u["id"] == UNIT)
            calc.validate_new(row, manifest, unit_meta)
            calc.validate_grade(row, unit_meta)
            calc.score(row)
            with runner.rows_lock("fixcheck", "codex"):
                result = append_once(state / "attempts-fixcheck-codex.jsonl",
                                     state / "rows-fixcheck-codex.jsonl", row)
            print("Recovery ledgers synchronized; existing flags:", result)
            return
        if proposed.exists() or (state / ROOT / "grade-recovery").exists():
            raise ValueError("recovery already prepared or grading started; inspect without regrading")
        input_hash = original_inputs(state)
        start = [r for r in rows(state / "starts-fixcheck-codex.jsonl") if r["root"] == ROOT]
        if len(start) != 1 or start[0]["attempt"] != 1:
            raise ValueError("ambiguous attempt start")
        if any(r["unit"] == UNIT for r in rows(state / "attempts-fixcheck-codex.jsonl")
               + rows(state / "rows-fixcheck-codex.jsonl")):
            raise ValueError("task already recorded")
        root = state / ROOT
        if len(list((root / "home/.codex/sessions").rglob("*.jsonl"))) != 2:
            raise ValueError("unexpected session home contents")
        replay = []
        fields = ("tokens_total", "tokens_noncache", "provider", "root_models",
                  "root_model_missing", "model", "models_used", "context", "listed_skills",
                  "listed_tools", "skills", "agents", "threads", "tools", "blocked", "evidence")
        for old in rows(state / "rows-fixcheck-codex.jsonl"):
            for i, saved in enumerate(old["sessions"], 1):
                reconstructed = session(runner, state / old["root"], i)
                mismatch = [key for key in fields if reconstructed[key] != saved[key]]
                if mismatch:
                    raise ValueError("unaffected-session replay mismatch: " + repr(mismatch))
                replay.append({"unit": old["unit"], "session": i, "matched_fields": list(fields)})
        sessions = [session(runner, root, 1), session(runner, root, 2, True)]
        if [s["tokens_total"] for s in sessions] != [165952, 262326]:
            raise ValueError("reviewed recovery usage changed")
        unit = next(u for u in read(state / "units_B.json")["units"] if u["id"] == UNIT)
        original_inputs(state)
        grade = runner.grade(unit, str(root / "work/proj"), str(root / "grade-recovery"),
                             ref=manifest["runtime"]["arms"]["O"]["commit"])
        original_inputs(state)
        row = {key: value for key, value in start[0].items() if key not in ("event", "time")}
        row.update(type=unit["type"], started=start[0]["time"], finished=None,
                   arm_commit=manifest["runtime"]["arms"]["O"]["commit"], carry=unit.get("carry", "home"),
                   sessions=sessions, flags=["offline ENOSPC recovery; exact exit/wall-time unavailable"],
                   model_asked="gpt-6.1-sol", cap=None, cap_decision=None, grade=grade, score=grade["score"],
                   tokens_total=sum(s["tokens_total"] for s in sessions),
                   tokens_noncache=sum(s["tokens_noncache"] for s in sessions), seconds=None,
                   top_level_added=sorted(set(os.listdir(root / "work/proj")) - set(os.listdir(runner.arm_dir("N"))))[:50],
                   recovery={"method": "same completed answer; frozen mechanical grade; complete parent usage",
                             "script_sha256": sha(__file__), "input_index_sha256": input_hash,
                             "protocol_note": "RECOVERY.md", "exact_original_finish_time": "not persisted"})
        if grade["error"] or grade["score"] is None:
            row["not_run"] = "recovery grading failed: " + (grade["error"] or "no score")
        write(proposed, row)
        if row.get("not_run"):
            raise ValueError(row["not_run"])
        unit_meta = next(u for u in manifest["units"] if u["id"] == UNIT)
        calc.validate_new(row, manifest, unit_meta)
        calc.validate_grade(row, unit_meta)
        calc.score(row)
        write(state / "RECOVERY_REPORT.json", {"row_sha256": sha(proposed), "script_sha256": sha(__file__),
              "manifest_sha256": sha(fx.MANIFEST), "original_inputs_unchanged": True,
              "replay": replay, "models_called": 0, "ledger_appended": False})
        print("Proposed row prepared and offline-validated; 6 unaffected sessions replayed; no ledger append.")


if __name__ == "__main__":
    main()
