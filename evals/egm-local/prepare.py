#!/usr/bin/env python3
"""Prepare fresh, answer-free workspaces for a human-dispatched Codex experiment.

This program never calls a model, Claude, Codex, or a subprocess. It does not
dispatch agents. The specification/rubric stays outside every reviewer workspace.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import random
import shutil
from contextlib import redirect_stdout

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify():
    spec = json.loads((HERE / "spec.json").read_text(encoding="utf-8"))
    actual = digest(canonical(spec))
    if (HERE / "spec.sha256").read_text(encoding="utf-8").split()[0] != actual:
        raise ValueError("Local experiment specification changed after registration")
    observed = {p.relative_to(HERE).as_posix(): digest(p.read_bytes().replace(b"\r\n", b"\n"))
                for p in sorted((HERE / "cases").rglob("*")) if p.is_file()}
    if observed != spec["case_hashes"]:
        raise ValueError("Case files changed after registration")
    for name, expected in spec["prompt_hashes"].items():
        if digest((HERE / name).read_bytes().replace(b"\r\n", b"\n")) != expected:
            raise ValueError("Review/grading prompts changed after registration")
    if spec["inputs"]["prepare.py"] != digest((HERE / "prepare.py").read_bytes().replace(b"\r\n", b"\n")):
        raise ValueError("Workspace preparation changed after registration")
    helper = REPO / "evals/egm-pilot/pilot_common.py"
    module_spec = importlib.util.spec_from_file_location("local_experiment_common", helper)
    pc = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(pc)
    if spec["inputs"]["oaw_source"] != pc.tree_digest(REPO, ("scripts", "templates")):
        raise ValueError("OAW source changed after registration")
    return spec, actual


def prepare(output):
    spec, spec_hash = verify()
    output = Path(os.path.abspath(output))
    if output.is_relative_to(REPO) or output.exists():
        raise ValueError("Choose a fresh output directory outside the repository")
    output.mkdir(parents=True)
    module_spec = importlib.util.spec_from_file_location("local_experiment_installer", REPO / "scripts/oaw.py")
    installer = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(installer)
    notes = {
        "orders": "ADR-001 r2 (accepted 2026-09-10): PostgreSQL inventory/reservations; requests are idempotent per order_id. Source: docs/adr-001-storage.md. Verify against current source.",
        "events": "ADR-004 r1 (accepted 2026-08-12): events may reorder/redeliver; shipment versions are monotonic; never log authentication tokens. Source: docs/adr-004-events.md. Verify against current source.",
        "clean": "Historical note, verified 2026-07-01 against ADR-002 r2: all services use PostgreSQL only. Source: docs/adr-002-storage.md. This note may be superseded; verify current accepted decisions before relying on it.",
    }
    runs = []
    for case in spec["cases"]:
        for repeat in range(1, spec["repeats"] + 1):
            for arm in spec["arms"]:
                workspace = output / f"{case}-r{repeat}-{arm}"
                shutil.copytree(HERE / "cases" / case, workspace)
                if arm == "C":
                    with redirect_stdout(io.StringIO()):
                        code = installer.main(["init", "--target", str(workspace), "--host", "codex", "--json"])
                    if code:
                        raise ValueError("OAW installation failed")
                    (workspace / ".agents/memory.md").write_text("# Project evidence\n\n" + notes[case] + "\n", encoding="utf-8")
                runs.append({"id": workspace.name, "case": case, "repeat": repeat, "arm": arm,
                             "workspace": str(workspace), "report": str(output / "reports" / (workspace.name + ".json")),
                             "initial_sha256": {p.relative_to(workspace).as_posix(): digest(p.read_bytes().replace(b"\r\n", b"\n"))
                                                for p in workspace.rglob("*") if p.is_file()}})
    blocks = [(case, repeat) for case in spec["cases"] for repeat in range(1, spec["repeats"] + 1)]
    random.Random(spec["dispatch_seed"]).shuffle(blocks)
    lookup = {(run["case"], run["repeat"], run["arm"]): run for run in runs}
    ordered = []
    arms = list(spec["arms"])
    for case, repeat in blocks:
        shift = (spec["cases"].index(case) + repeat - 1) % len(arms)
        ordered.extend(lookup[case, repeat, arm] for arm in arms[shift:] + arms[:shift])
    manifest = {"schema_version": 1, "spec_sha256": spec_hash, "model_calls": 0,
                "source_sha256": spec["inputs"]["oaw_source"], "runs": ordered}
    (output / "reports").mkdir()
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_workspace(run):
    workspace = Path(run["workspace"])
    for name, expected in run["initial_sha256"].items():
        path = workspace / name
        if not path.is_file() or digest(path.read_bytes().replace(b"\r\n", b"\n")) != expected:
            raise ValueError("Trial input changed: " + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        _, value = verify()
        print(json.dumps({"intact": True, "spec_sha256": value, "model_calls": 0}))
    elif args.out:
        result = prepare(args.out)
        print(json.dumps({"prepared": len(result["runs"]), "spec_sha256": result["spec_sha256"], "model_calls": 0}))
    else:
        parser.error("supply --verify or --out")


if __name__ == "__main__":
    main()
