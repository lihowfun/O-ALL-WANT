"""X2 out-of-workspace read scan (PREREG.md, "讀到工作區以外"). For every answering run (rows and deviations), read
the raw Claude transcript or the Codex event stream plus every rollout in the run's thread tree, collect the text of
each tool call (Claude tool_use inputs, subagents included; Codex exec / shell / function calls), and flag:
  - absolute paths outside the run's own workspace (system paths such as /usr, /bin, /dev, /proc, /etc are listed
    separately and are not flagged),
  - parent-directory traversal ("../"), home references ("~/", "$HOME"),
  - the names OAW-records, spec.json, frozen/, records/, verification.json, and other runs' folders.
Flags are evidence for the judge, not verdicts: Codex decides whether a flagged run is excluded.

    python3 x2_scan.py --runs RUNS_DIR --parts claude-a,claude-b,codex-a,codex-b --out scan.json
"""
import argparse
import glob
import json
import os
import re

PATH = re.compile(r"(?<![\w.~$])(/(?:[\w.@+-]+/?)+)")
SYSTEM = ("/usr/", "/bin/", "/dev/", "/proc/", "/etc/", "/lib", "/sbin/", "/opt/conda", "/sys/")
NAMES = re.compile(r"OAW-records|spec\.json|frozen/|verification\.json|\brecords/|x2_\w+\.py|only-[ab]\.txt|rows\.jsonl")
TRAVERSE = re.compile(r"(?:^|[\s\"'=(:])\.\.(?:/|(?=[\s\"';)]|$))|~/|\$HOME|\$\{HOME\}")


def claude_calls(path):
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        message = event.get("message") or {}
        if event.get("type") != "assistant" or not isinstance(message.get("content"), list):
            continue
        for block in message["content"]:
            if block.get("type") == "tool_use":
                yield block.get("name", "?"), json.dumps(block.get("input", {}), ensure_ascii=False)


def codex_calls(path):
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        item = event.get("item") or {}
        if item.get("type") == "command_execution":
            yield "command_execution", item.get("command", "")
        payload = event.get("payload") or {}
        kind = payload.get("type")
        if kind == "custom_tool_call":
            yield payload.get("name", "?"), payload.get("input", "")
        elif kind == "function_call":
            arguments = payload.get("arguments", "")
            if payload.get("namespace") == "collaboration":  # agent messages: "target" is an agent path such as /root
                try:
                    arguments = json.dumps({k: v for k, v in json.loads(arguments).items() if k != "target"})
                except (ValueError, AttributeError):
                    pass
            yield payload.get("name", "?"), arguments
        elif kind == "local_shell_call":
            yield "local_shell", json.dumps(payload.get("action", {}))


ROOTS = {name for name in os.listdir("/")}


def scan_text(text, ws):
    """Returns (flags, system, probes). A path counts only if its first segment is a real top-level directory here;
    "/v1/carts" or "<root>/agents/x.md" inside prose is not a filesystem path. An AGENTS.md lookup in an ancestor of the
    workspace, or the ancestor itself, is a probe (Codex looks for instruction files up the tree), listed apart."""
    flags, system, probes = set(), set(), set()
    for match in PATH.findall(text):
        p = match.rstrip("/.,;:)'\"")
        if not p or p == "/" or p.split("/")[1] not in ROOTS or p.startswith(ws + "/") or p == ws:
            continue
        if p.startswith(SYSTEM) or p in ("/usr", "/bin", "/dev/null", "/tmp", "/etc"):
            system.add(p)
            continue
        bare = p[:-len("/AGENTS.md")] if p.endswith("/AGENTS.md") else p
        if ws.startswith(bare.rstrip("/") + "/") or bare in ("", "/tmp"):
            probes.add(p)
            continue
        flags.add("path:" + p)
    for match in NAMES.findall(text):
        flags.add("name:" + match)
    for match in TRAVERSE.findall(text):
        flags.add("traverse:" + match.strip())
    return flags, system, probes


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", required=True)
    parser.add_argument("--parts", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    report = []
    for part in args.parts.split(","):
        base = os.path.join(args.runs, part)
        cell = part.split("-")[0]
        for name in ("rows.jsonl", "deviations.jsonl"):
            path = os.path.join(base, name)
            if not os.path.exists(path):
                continue
            for line in open(path, encoding="utf-8"):
                row = json.loads(line)
                key = row["arm"] + "-" + row["id"] + ("" if row.get("rep", 1) == 1 and "cal" not in part else f".r{row.get('rep', 1)}")
                tag = f"{key}.a{row.get('attempt', 1)}"
                ws = os.path.realpath(os.path.join(base, "ws", key))
                sources = [os.path.join(base, "raw", tag + ".jsonl")]
                sources += sorted(glob.glob(os.path.join(base, "raw", tag + "-rollouts", "*.jsonl")))
                calls, flags, system, probes = 0, {}, set(), set()
                for src in sources:
                    if not os.path.exists(src):
                        flags.setdefault("missing-source:" + os.path.basename(src), []).append("")
                        continue
                    reader = claude_calls if cell == "claude" else codex_calls
                    for tool, text in reader(src):
                        calls += 1
                        found, sys_paths, probe = scan_text(text, ws)
                        system |= sys_paths
                        probes |= probe
                        for flag in found:
                            flags.setdefault(flag, []).append(f"{tool}: {text[:240]}")
                report.append({"part": part, "file": name, "arm": row["arm"], "id": row["id"], "rep": row.get("rep", 1),
                               "attempt": row.get("attempt", 1), "tool_calls": calls, "sources": len(sources),
                               "flags": {k: v[:3] for k, v in sorted(flags.items())}, "system_paths": sorted(system),
                               "ancestor_probes": len(probes)})
    json.dump(report, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    flagged = [r for r in report if r["flags"]]
    print(f"{len(report)} runs scanned, {sum(r['tool_calls'] for r in report)} tool calls, {len(flagged)} with flags, "
          f"{sum(1 for r in report if r['ancestor_probes'])} with ancestor AGENTS.md probes")
    for r in flagged:
        print(f"  {r['part']} {r['arm']}-{r['id']} r{r['rep']} ({r['file']}): {sorted(r['flags'])[:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
