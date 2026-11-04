"""Arm G for the code-map Stage 0-alpha harness: graphify 0.9.101 through its own CLI, as an agent would use it.

Written on 2026-11-04 AFTER the R and S results were known (a recorded deviation, not pre-registered).
cwd is the arm's corpus copy; the setup step (`graphify update .`) has built graphify-out/graph.json there.

  find "<text>"   -> graphify query "<text>"            (default 2000-token budget); files in the order printed
  callers SYMBOL  -> graphify affected SYMBOL --relation calls --depth 1; on "Ambiguous", retry once with the
                     node id of the candidate outside example/ (graphify's own path::symbol hint stays ambiguous)
  path A B        -> graphify path A B; the printed chain of labels is mapped back to files through graph.json

Text mode prints graphify's own output (what an agent reads). --json prints {"results": [{"path": ...}]}.
"""
import json
import os
import re
import subprocess
import sys

GRAPHIFY = os.environ.get("G_ARM_GRAPHIFY") or os.path.join(os.path.dirname(sys.executable), "graphify")
HOME = os.environ.get("G_ARM_HOME") or os.path.expanduser("~/oaw-graphify-run/home")


def graphify(*argv):
    env = {"HOME": HOME, "PATH": os.path.dirname(GRAPHIFY) + ":/usr/bin:/bin", "LANG": "C.UTF-8", "TERM": "dumb"}
    done = subprocess.run([GRAPHIFY, *argv], capture_output=True, text=True, env=env, timeout=300)
    return done.stdout + done.stderr


def ordered(paths):
    seen, out = set(), []
    for path in paths:
        if path and path not in seen:
            seen.add(path)
            out.append(path)
    return out


def find(text):
    output = graphify("query", text)
    paths = re.findall(r"^NODE .*?\[src=([^\s\]]+)", output, flags=re.M)
    return output, ordered(paths)


def callers(symbol):
    output = graphify("affected", symbol, "--relation", "calls", "--depth", "1")
    if output.startswith("Ambiguous"):
        ids = re.findall(r"^\s+(\S+)\n\s+id: (\S+)", output, flags=re.M)
        chosen = next((node for path, node in ids if not path.startswith("example/")), ids[0][1] if ids else None)
        if chosen:
            output += "\n" + graphify("affected", chosen, "--relation", "calls", "--depth", "1")
    paths = re.findall(r"^- .*?\] (\S+?):L\d+", output, flags=re.M)
    return output, ordered(paths)


def path(source, target):
    output = graphify("path", source, target)
    with open(os.path.join("graphify-out", "graph.json"), encoding="utf-8") as handle:
        graph = json.load(handle)
    nodes = {node["id"]: node for node in graph["nodes"]}
    neighbors = {}
    for link in graph["links"]:
        neighbors.setdefault(link["source"], set()).add(link["target"])
        neighbors.setdefault(link["target"], set()).add(link["source"])
    chain_line = next((line for line in output.splitlines() if "-->" in line), "")
    labels = [part.strip() for part in re.split(r"--\S+(?: \[[A-Z]+\])?-->", chain_line) if part.strip()]
    files = []
    current = next((nid for nid, node in nodes.items()
                    if node.get("source_file") == source and node.get("label") == os.path.basename(source)), None)
    if labels and current:
        files.append(source)
        for label in labels[1:]:
            step = next((nid for nid in sorted(neighbors.get(current, ())) if nodes[nid].get("label") == label), None)
            if step is None:
                break
            current = step
            files.append(nodes[step].get("source_file"))
    return output, ordered(files)


def main(argv):
    as_json = "--json" in argv
    argv = [item for item in argv if item != "--json"]
    sub, args = argv[0], argv[1:]
    if sub == "find":
        output, paths = find(" ".join(args))
    elif sub == "callers":
        output, paths = callers(args[0])
    elif sub == "path":
        output, paths = path(args[0], args[1])
    else:
        print(f"unsupported subcommand: {sub}", file=sys.stderr)
        return 2
    if as_json:
        print(json.dumps({"results": [{"path": item} for item in paths]}))
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
