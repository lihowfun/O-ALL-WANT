"""I16 replay (PREREG.md): run every reported defect's steps mechanically, so graders judge support on observed
behavior instead of the tester's word.

For each graded row and each defect in its report, two fresh workspaces are built exactly as the tester's was: the
case build (the journey's seeded defect applied, if any) and the clean build (no defect). The steps run in order
with bash inside bubblewrap with no network and no host state, each step under 60 seconds. Output is normalized
(the workspace path becomes <ws>) and truncated. A clean-control journey has one build, so only one replay.

    python3 i16_replay.py --cases FROZEN --oaw-src DIR --rows A/rows.jsonl,B/rows.jsonl --out replay.jsonl
Every entry is bound to the replayer and runner versions, the spec, the case files, the report and both built
tools; resume refuses an entry whose bindings differ, and a build whose tool digest differs from the spec stops.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from i16_run import base_env, build, tree_digest  # noqa: E402

STEP_TIMEOUT, MAX_STEPS, KEEP = 60, 25, 1500


def sandboxed_bash(work, command):
    argv = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
            "--tmpfs", os.environ["HOME"], *[x for h in os.environ["I16_HIDE"].split(":") if h for x in ("--tmpfs", h)],
            "--bind", work, work, "--chdir", work, "--unshare-net", "--die-with-parent", "/bin/bash", "-c", command]
    env = base_env(work, "")
    try:
        done = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=STEP_TIMEOUT, errors="replace")
        return done.returncode, done.stdout, done.stderr
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return "timeout", out, err


def clip(text, work):
    text = (text or "").replace(work, "<ws>")
    return text if len(text) <= KEEP else text[:KEEP // 2] + f"\n...[{len(text) - KEEP} chars cut]...\n" + text[-KEEP // 2:]


def replay(case_dir, oaw_src, steps, with_defect, base, want_digest):
    work = tempfile.mkdtemp(prefix="rp-", dir=base)
    try:
        facts = build(case_dir, oaw_src, work, with_defect=with_defect)
        if facts["oaw_digest"] != want_digest:
            raise SystemExit(f"{case_dir}: replay build differs from the frozen digest")
        out = []
        for step in steps[:MAX_STEPS]:
            code, stdout, stderr = sandboxed_bash(work, str(step))
            out.append({"step": str(step)[:400], "exit": code, "stdout": clip(stdout, work), "stderr": clip(stderr, work)})
        if len(steps) > MAX_STEPS:
            out.append({"step": f"[{len(steps) - MAX_STEPS} more steps not run]", "exit": None, "stdout": "", "stderr": ""})
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


def row_key(row):
    return f"{row['cell']}|{row['arm']}|{row['id']}" + (f"|r{row['rep']}" if row.get("rep", 1) != 1 else "")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--cases", required=True)
    p.add_argument("--oaw-src", required=True)
    p.add_argument("--rows", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    spec = json.load(open(os.path.join(a.cases, "spec.json"), encoding="utf-8"))
    me = hashlib.sha256(b"".join(open(os.path.join(HERE, n), "rb").read() for n in ("i16_replay.py", "i16_run.py"))).hexdigest()
    spec_sha = hashlib.sha256(open(os.path.join(a.cases, "spec.json"), "rb").read()).hexdigest()
    if tree_digest(a.oaw_src) != spec["oaw_src_digest"]:
        raise SystemExit("the OAW source differs from the frozen spec")
    done = {}
    if os.path.exists(a.out):
        for line in open(a.out, encoding="utf-8"):
            old = json.loads(line)
            if old["replayer_sha256"] != me or old["spec_sha256"] != spec_sha:
                raise SystemExit(f"{a.out}: written by another replayer or for another spec")
            done[(old["key"], old["index"])] = (old["report_sha256"], old.get("row_runner_sha256"))
    open(a.out, "a", encoding="utf-8").close()  # an empty replay file is a valid result: no defects reported
    base = tempfile.mkdtemp(prefix="i16rp-", dir=os.environ.get("I16_WS_ROOT") or None)
    for path in a.rows.split(","):
        for line in open(path, encoding="utf-8"):
            row = json.loads(line)
            defects = ((row.get("report") or {}).get("defects") or []) if isinstance(row.get("report"), dict) else []
            case_dir = os.path.join(a.cases, "cases", row["id"])
            if tree_digest(case_dir) != spec["case_digests"][row["id"]] or row.get("spec_sha256") != spec_sha:
                raise SystemExit(f"{row['id']}: case files or the row's spec differ from the frozen spec")
            report_sha = hashlib.sha256(json.dumps(row.get("report"), sort_keys=True).encode()).hexdigest()
            for index, defect in enumerate(defects):
                key = row_key(row)
                if (key, index) in done:
                    if done[(key, index)] != (report_sha, row.get("runner_sha256")):
                        raise SystemExit(f"{key} #{index}: replayed for another report or runner")
                    continue
                steps = defect.get("steps") if isinstance(defect, dict) else None
                entry = {"key": key, "index": index, "replayer_sha256": me, "spec_sha256": spec_sha,
                         "row_runner_sha256": row.get("runner_sha256"),
                         "case_digest": spec["case_digests"][row["id"]], "report_sha256": report_sha,
                         "case_build": spec["built_digests"][row["id"]], "clean_build": spec["oaw_src_digest"]}
                if not isinstance(steps, list) or not steps:
                    entry["case"] = entry["clean"] = None
                    entry["why"] = "no steps"
                else:
                    entry["case"] = replay(case_dir, a.oaw_src, steps, True, base, spec["built_digests"][row["id"]])
                    entry["clean"] = (replay(case_dir, a.oaw_src, steps, False, base, spec["oaw_src_digest"])
                                      if spec["kinds"][row["id"]] == "defect" else "same build (clean control)")
                with open(a.out, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
                print(f"replayed {key} #{index}: {len(steps or [])} steps", flush=True)
    shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
