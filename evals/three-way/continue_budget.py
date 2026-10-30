#!/usr/bin/env python3
"""Explicit budget-only continuation. Never retry a dispatched failed model call.

Keeps bench.py and the original protocol frozen. Completed calls are reused with
the exact same prompt; a not-started call may be dispatched once. This is one
continued cohort, not an independent repeat or a new fixed-budget experiment.
"""
import argparse
import shutil
import sys
import time
from pathlib import Path
import bench


class ContinuedRunner(bench.Runner):
    def call(self, ident, workspace, prompt):
        dest = self.out / "raw" / ident
        if dest.exists():
            result = dest / "result.json"
            if result.exists():
                row = bench.read(result)
                if row["status"] != "complete":
                    raise ValueError("Dispatched failure cannot be retried: " + ident)
                expected = prompt + f"\nAvailable Python executable (if needed): {sys.executable}\n\n" + bench.FINAL_FORMAT
                if (dest / "prompt.txt").read_text(encoding="utf-8") != expected:
                    raise ValueError("Prompt drift: " + ident)
                return bench.read(dest / "answer.json")
            # Original budget check creates a directory before dispatch. Only an
            # empty directory proves this attempt never reached a model call.
            if any(dest.iterdir()) or not dest.resolve().is_relative_to((self.out / "raw").resolve()):
                raise ValueError("Ambiguous interrupted call: " + ident)
            dest.rmdir()
        return super().call(ident, workspace, prompt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--codex", required=True)
    parser.add_argument("--total-token-limit", type=int, required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    if bench.read(out / "protocol.json")["id"] != "egm-oaw-acceptance-pilot-20261030-v1":
        raise ValueError("Historical v1 budget controller only; current cohorts are not resumable here")
    amendment = out / "budget-amendment.json"
    if amendment.exists():
        raise ValueError("One explicit amendment only; refusing repeat continuation")
    previous = bench.read(out / "execution.json")
    for name in ("execution.json", "runtime.json"):
        shutil.copy2(out / name, out / ("before-amendment-" + name))
    old_evidence = bench.tree(out / "raw")
    runner = ContinuedRunner(args)
    old_limit = runner.spec["limits"]["input_plus_output_tokens"]
    if args.total_token_limit <= old_limit:
        raise ValueError("Supplement must explicitly increase total token budget")
    runner.spec["limits"]["input_plus_output_tokens"] = args.total_token_limit
    runner.rows = previous["rows"][:]
    runner.total = previous["total_input_plus_output_tokens"]
    runner.output = previous["total_output_tokens"]
    # Preserve the original wall-time origin across process restart.
    first = min(p.stat().st_mtime for p in (out / "raw").glob("*/prompt.txt"))
    runner.started = time.monotonic() - (time.time() - first)
    bench.write(amendment, {"reason": "No-tool probe understated cumulative input across tool turns; budget-only supplement before inspecting task quality or grading. All tasks, repeats, prompts, sources, rubric, output limit and wall-time limit unchanged.", "original_token_limit": old_limit, "new_total_token_limit": args.total_token_limit, "completed_calls_reused": [row["id"] for row in previous["rows"]], "existing_raw_hashes": old_evidence, "continuation_sha256": bench.sha(__file__), "original_runner_sha256": bench.sha(bench.__file__), "automatic_retries": 0, "independent_repeat": False})
    original_copy = bench.shutil.copytree

    def preserve_existing(source, target, *positional, **keywords):
        target = Path(target).resolve()
        if target.exists():
            if not any(target.is_relative_to((out / name).resolve()) for name in ("workers", "snapshot-files")):
                raise ValueError("Unexpected existing copy target")
            return target
        return original_copy(source, target, *positional, **keywords)

    bench.shutil.copytree = preserve_existing
    runner.run()
    after = bench.tree(out / "raw")
    if any(after.get(name) != value for name, value in old_evidence.items()):
        raise ValueError("Pre-amendment evidence changed")


if __name__ == "__main__":
    main()
