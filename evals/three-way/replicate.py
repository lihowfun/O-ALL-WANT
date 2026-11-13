#!/usr/bin/env python3
"""Run the separately registered identical-snapshot receiver diagnostic."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import random
import shutil
import threading
import time
import bench


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--codex", required=True)
    args = parser.parse_args()
    cohort, out = Path(args.cohort).resolve(), Path(args.out).resolve()
    if out.exists() or out.is_relative_to(bench.HERE.parents[1]):
        raise ValueError("Use a fresh private output")
    manifest = bench.read(cohort / "manifest.json")
    if manifest["runner_sha256"] != bench.sha(bench.__file__):
        raise ValueError("Original runner changed")
    spec = bench.read(bench.HERE / "replication-protocol.json")
    tasks = []
    for item in manifest["trajectories"]:
        original_id = item["id"] + "-s2"
        if bench.read(cohort / "raw" / original_id / "result.json")["status"] != "complete":
            raise ValueError("Original S2 missing")
        source = cohort / "snapshot-files" / (item["id"] + "-s1")
        expected = bench.read(cohort / "snapshots" / (item["id"] + "-s1.json"))
        if bench.tree(source) != expected:
            raise ValueError("Saved S1 snapshot drift")
        prompt = (cohort / "raw" / original_id / "prompt.txt").read_text(encoding="utf-8")
        marker = "\nBefore substantive work, read artifacts/io-"
        if prompt.count(marker) != 1 or not prompt.endswith(bench.FINAL_FORMAT):
            raise ValueError("Cannot preserve exact original receiver prompt")
        base_prompt = prompt.split(marker, 1)[0]
        for repeat in (2, 3):
            ident = item["id"] + f"-receiver{repeat}"
            target = out / "work" / ident
            shutil.copytree(source, target)
            tasks.append({"id": ident, "arm": item["arm"], "name": item["name"], "original_s2": original_id, "workspace": str(target), "snapshot_sha256": expected, "prompt": base_prompt})
    random.Random(20261101).shuffle(tasks)
    bench.write(out / "protocol.json", spec)
    bench.write(out / "manifest.json", {"tasks": tasks, "runner_sha256": bench.sha(bench.__file__), "replication_runner_sha256": bench.sha(__file__)})
    runner = bench.Runner.__new__(bench.Runner)
    runner.out, runner.cli, runner.spec = out, args.codex, spec
    runner.started, runner.lock = time.monotonic(), threading.Lock()
    runner.abort = threading.Event()
    runner.total = runner.output = 0
    runner.rows = []

    def call(item):
        answer = runner.call(item["id"], Path(item["workspace"]), item["prompt"])
        workspace = Path(item["workspace"])
        for name, expected in item["snapshot_sha256"].items():
            protected = name.startswith(("docs/decisions/", "docs/history/", "method/", "scripts/", ".agents/skills/")) or name in ("AGENTS.md", "CLAUDE.md", "docs/imported-message.txt")
            if protected and (not (workspace / name).is_file() or bench.sha(workspace / name) != expected):
                runner.abort.set()
                raise ValueError("Copied source mutated: " + item["id"] + "/" + name)
        bench.write(out / "reports" / (item["id"] + ".json"), answer)
        # Each receiver can write its own handoff, never another receiver's copy.
        bench.write(out / "after" / (item["id"] + ".json"), bench.tree(Path(item["workspace"])))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(call, item) for item in tasks]
            for future in futures:
                future.result()
    finally:
        bench.write(out / "execution.json", {"rows": runner.rows, "total_input_plus_output_tokens": runner.total, "total_output_tokens": runner.output})


if __name__ == "__main__":
    main()
