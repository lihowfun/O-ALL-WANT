#!/usr/bin/env python3
"""Run the PRE-02 zero-context goldfish reviews (D10/D15) with the Claude CLI.

Each packet in packets/ is sent on stdin to `claude -p` started in a fresh empty
folder outside every project, with all tools, MCP servers, slash commands and
user/local settings turned off. The init event is recorded to prove zero context.
Results go to results/<packet>.json. Standard library only.

    python3 review-kit/pre02/run_goldfish.py            # run every packet
    python3 review-kit/pre02/run_goldfish.py --dry-run  # show what would run
    python3 review-kit/pre02/run_goldfish.py --only plan
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FLAGS = ["-p", "--tools", "", "--strict-mcp-config", "--disable-slash-commands",
         "--setting-sources", "project", "--output-format", "stream-json", "--verbose"]
EMPTY_KEYS = ("tools", "mcp_servers", "slash_commands", "skills", "plugins", "agents")


def run_one(claude, packet_path, timeout):
    with open(packet_path, encoding="utf-8") as fh:
        packet = fh.read()
    workdir = tempfile.mkdtemp(prefix="oaw-goldfish-")
    argv = [claude] + FLAGS
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        proc = subprocess.run(argv, input=packet, cwd=workdir, capture_output=True,
                              text=True, encoding="utf-8", timeout=timeout)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    events = []
    for line in proc.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    checks = {k: (len(init.get(k) or []) == 0) for k in ("tools", "mcp_servers", "slash_commands", "skills")
              if k in init}
    # Built-in plugins and agent types are always listed; they are inert here because
    # the goldfish has no tools (no Agent tool, nothing to read), so check that instead.
    checks["plugins_builtin_only"] = all(str(p.get("source", "")).endswith("@builtin")
                                         for p in init.get("plugins") or [] if isinstance(p, dict))
    checks["agents_unusable_without_tools"] = checks.get("tools", False)
    checks["cwd_is_fresh_temp"] = os.path.basename(str(init.get("cwd", ""))).startswith("oaw-goldfish-")
    auto_mem = str((init.get("memory_paths") or {}).get("auto", ""))
    checks["auto_memory_empty"] = not os.path.isdir(auto_mem) or not os.listdir(auto_mem)
    text = result.get("result") or ""
    block = re.findall(r"```json\s*(\{.*\})\s*```", text, re.S)
    review = None
    if block:
        try:
            review = json.loads(block[-1])
        except ValueError:
            review = None
    canary = (review or {}).get("canary", "")
    zero = bool(init) and all(checks.values()) and str(canary).strip().lower() == "none"
    return {
        "packet": os.path.basename(packet_path),
        "started_at": started,
        "launch": {"argv": ["claude"] + FLAGS, "stdin": "packet", "cwd": "fresh empty temp folder"},
        "exit_code": proc.returncode,
        "stderr_tail": proc.stderr[-2000:],
        "init_event": {k: init.get(k) for k in ("cwd", "model", "claude_code_version", "permissionMode",
                                                "apiKeySource", "memory_paths", "output_style") + EMPTY_KEYS
                       if k in init},
        "init_checks": checks,
        "canary": canary,
        "zero_context_verified": zero,
        "usage": result.get("usage"),
        "total_cost_usd": result.get("total_cost_usd"),
        "review": review,
        "raw_result_if_unparsed": None if review else text[-20000:],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--claude", default=shutil.which("claude") or "claude")
    ap.add_argument("--only", action="append", help="packet name without .md (repeatable)")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    pdir, rdir = os.path.join(HERE, "packets"), os.path.join(HERE, "results")
    names = sorted(n for n in os.listdir(pdir) if n.endswith(".md"))
    if args.only:
        names = [n for n in names if n[:-3] in args.only]
    if not names:
        sys.exit("no packets selected")
    version = subprocess.run([args.claude, "--version"], capture_output=True, text=True).stdout.strip()
    print("claude:", args.claude, version or "(version unknown)")
    if args.dry_run:
        for n in names:
            print("would run", n, os.path.getsize(os.path.join(pdir, n)), "bytes:",
                  " ".join(["claude"] + [f if f else '""' for f in FLAGS]))
        return 0
    os.makedirs(rdir, exist_ok=True)
    failed = 0
    for n in names:
        print("running", n, "...", flush=True)
        rec = run_one(args.claude, os.path.join(pdir, n), args.timeout)
        rec["host_version"] = version
        with open(os.path.join(rdir, n[:-3] + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1)
        found = len((rec["review"] or {}).get("findings") or [])
        print("  exit", rec["exit_code"], "| zero context verified:", rec["zero_context_verified"],
              "| findings:", found)
        if rec["exit_code"] != 0 or rec["review"] is None:
            failed += 1
            print("  stderr:", rec["stderr_tail"][-400:].strip())
    print("results in", rdir)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
