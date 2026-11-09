"""I16 positive control (PREREG.md, EVAL_PROTOCOL "量偵測能力時，加一組正對照"): before any graded tester run, check
that the grading pipeline credits a correct, reproducible report of each planted defect.

For each defect journey a synthetic report is written from the frozen truth: one defect whose only step runs the
journey's own oracle (which reproduces the defect on the case build). It is replayed with i16_replay.py and graded
by both families with i16_grade.py, exactly as tester reports are. The control passes only if both families credit
the planted defect on every journey. A failed control stops the study before calibration; the owner and Codex see
it (PREREG).

    python3 i16_controls.py build --cases FROZEN --out control-rows.jsonl
    (replay and grade control-rows.jsonl as usual, into control-replay.jsonl and control-grades-{opus,codex}.jsonl)
    python3 i16_controls.py check --cases FROZEN --rows control-rows.jsonl --grades A,B --out controls.json
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("step", choices=("build", "check"))
    p.add_argument("--cases", required=True)
    p.add_argument("--rows")
    p.add_argument("--grades")
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    spec_path = os.path.join(a.cases, "spec.json")
    spec = json.load(open(spec_path, encoding="utf-8"))
    spec_sha = hashlib.sha256(open(spec_path, "rb").read()).hexdigest()
    defect = [j for j in spec["order"] if spec["kinds"][j] == "defect"]
    if a.step == "build":
        with open(a.out, "w", encoding="utf-8") as handle:
            for jid in defect:
                truth = spec["truth"][jid]
                oracle = open(os.path.join(a.cases, "cases", jid, "oracle.sh"), encoding="utf-8").read()
                report = {"completed": True, "checked": [truth["trigger"]], "notes": "",
                          "defects": [{"title": truth["rubric"][:300], "severity": truth["severity"],
                                       "steps": ["bash <<'ORACLE'\n" + oracle + "\nORACLE"],
                                       "expected": "the tool behaves as documented",
                                       "observed": truth["rubric"], "evidence": "see the replay of the step"}]}
                handle.write(json.dumps({"cell": "control", "arm": "P", "id": jid, "rep": 1, "kind": "defect",
                                         "spec_sha256": spec_sha, "case_digest": spec["case_digests"][jid],
                                         "built_digest": spec["built_digests"][jid], "runner_sha256": "control",
                                         "prompt_sha256": "control", "report": report}, ensure_ascii=False) + "\n")
        print(f"{len(defect)} control reports")
        return 0
    rows = {json.loads(l)["id"]: json.loads(l) for l in open(a.rows, encoding="utf-8")}
    grades = [json.loads(l) for path in a.grades.split(",") for l in open(path, encoding="utf-8")]
    result = {"spec_sha256": spec_sha, "journeys": {}, "pass": True}
    for jid in defect:
        report_sha = hashlib.sha256(json.dumps(rows[jid]["report"], sort_keys=True).encode()).hexdigest()
        got = {g["family"]: g for g in grades if g["id"] == jid and g["spec_sha256"] == spec_sha
               and g["report_sha256"] == report_sha}
        credit = {fam: bool(got.get(fam, {}).get("detected")) for fam in ("opus", "codex")}
        for fam, g in got.items():
            result.setdefault("versions", {}).setdefault(fam, set()).add((g["grader_sha256"], g.get("replayer_sha256")))
        result["journeys"][jid] = {"credited": credit, "notes": {f: got[f]["verdict"].get("note") for f in got}}
        result["pass"] = result["pass"] and all(credit.values())
    versions = result.get("versions", {})
    if any(len(v) != 1 for v in versions.values()) or set(versions) != {"opus", "codex"}:
        result["pass"] = False
    result["versions"] = {fam: list(next(iter(v))) for fam, v in versions.items() if len(v) == 1}
    result["inputs"] = {os.path.basename(x): hashlib.sha256(open(x, "rb").read()).hexdigest()
                        for x in [a.rows, *a.grades.split(",")]}
    json.dump(result, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("positive control:", "pass" if result["pass"] else "FAIL", json.dumps({j: v["credited"] for j, v in result["journeys"].items()}))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
