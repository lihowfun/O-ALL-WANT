#!/usr/bin/python3 -I
"""Side-call shim for the tasting arms (first `claude` on PATH in every arm).

The food's own model calls (TokenEconomizer's judge, redirect writer, fact proposer, and its
catalog probe) find `claude` on PATH. This shim runs the pinned CLI with the same setting
isolation as every arm session (`--setting-sources project,local` added to print-mode calls that
do not name one) and appends one usage line per call to $TASTE_SIDECALL_LOG. It forwards stdin,
stdout (line by line, so a caller can stop after the init event) and the exit code unchanged.
No prompt or answer text is logged.
"""
import json
import os
import subprocess
import sys
import time

REAL = "<set by setup.sh>"
argv = sys.argv[1:]
printing = "-p" in argv or "--print" in argv
if printing and "--setting-sources" not in argv:
    argv = argv + ["--setting-sources", "project,local"]
started = time.time()
proc = subprocess.Popen([REAL] + argv, stdin=sys.stdin, stdout=subprocess.PIPE)
chunks = []
for line in proc.stdout:
    chunks.append(line)
    sys.stdout.buffer.write(line)
    sys.stdout.buffer.flush()
code = proc.wait()
log = os.environ.get("TASTE_SIDECALL_LOG")
if printing and log:
    text = b"".join(chunks).decode("utf-8", "replace")
    result = None
    for piece in [text] + text.splitlines():
        try:
            event = json.loads(piece)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            result = event
    model_usage = (result or {}).get("modelUsage") or {}
    flags = [a for a in argv if a.startswith("--")]
    model = argv[argv.index("--model") + 1] if "--model" in argv else None
    entry = {"ts": round(started, 3), "seconds": round(time.time() - started, 2), "exit": code,
             "model_arg": model, "flags": flags, "result_seen": result is not None,
             "usage": (result or {}).get("usage"), "modelUsage": model_usage,
             "cost_usd": (result or {}).get("total_cost_usd"), "num_turns": (result or {}).get("num_turns")}
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
sys.exit(code)
