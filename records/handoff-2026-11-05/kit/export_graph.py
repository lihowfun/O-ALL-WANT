"""Export OAW's own code_index view of a repo as a JSON graph (files, imports, cross-file calls, hub functions)."""
import json, sys, os, subprocess
from collections import Counter, defaultdict

repo = os.path.abspath(sys.argv[1]); out = sys.argv[2]
sys.path.insert(0, os.path.join(repo, "scripts"))
import code_index as ci

index = ci.build_index(repo)
tables = index.tables()
files = {p: r for p, r in index.files.items() if r.get("py")}
edges_imp = index.import_edges()

def group(p):
    top = p.split("/")[0]
    if top == "scripts":
        return "scripts"
    if top == "tests":
        return "tests"
    if top in ("evals", "benchmarks"):
        return "evals"
    if top in ("templates",):
        return "templates"
    return "other"

nodes = {}
for p, r in files.items():
    py = r["py"]
    defs = py["defs"]
    nodes[p] = {"id": p, "group": group(p), "lines": len(index.files[p].get("lines", []) or []) if isinstance(index.files[p].get("lines"), list) else None,
                "size": r.get("size", 0), "funcs": sum(1 for d in defs if d[1] in ("function", "method", "async")),
                "classes": sum(1 for d in defs if d[1] == "class"), "defs": len(defs),
                "top": [d[0] for d in defs if "." not in d[0]][:400], "fan_in": 0, "fan_out": 0}

# line counts straight from disk
for p in nodes:
    try:
        with open(os.path.join(repo, p), "rb") as h:
            nodes[p]["lines"] = h.read().count(b"\n") + 1
    except OSError:
        pass

imp = Counter()
for src, lst in edges_imp.items():
    if src not in nodes:
        continue
    for line, scope, target, label in lst:
        if target in nodes and target != src:
            imp[(src, target)] += 1

calls = Counter(); def_in = Counter(); def_callers = defaultdict(set); unresolved = 0; resolved = 0
for p, r in files.items():
    for line, scope, chain in r["py"]["calls"]:
        try:
            got = index.resolve(p, scope, chain)
        except Exception:
            got = None
        if not got or got[0] != "def":
            unresolved += 1
            continue
        resolved += 1
        tp, q = got[1], got[2]
        if tp in nodes and tp != p:
            calls[(p, tp)] += 1
            def_in[(tp, q)] += 1
            def_callers[(tp, q)].add(p)

links = {}
for (s, t), n in imp.items():
    links.setdefault((s, t), {"source": s, "target": t, "imports": 0, "calls": 0})["imports"] = n
for (s, t), n in calls.items():
    links.setdefault((s, t), {"source": s, "target": t, "imports": 0, "calls": 0})["calls"] = n
for (s, t), l in links.items():
    nodes[s]["fan_out"] += 1; nodes[t]["fan_in"] += 1

hubs = []
for (tp, q), n in def_in.most_common(40):
    kind = tables["defs"].get((tp, q), ("?",))[0]
    hubs.append({"file": tp, "name": q, "kind": kind, "calls": n, "caller_files": len(def_callers[(tp, q)])})

# per-file: most-called functions (for the side panel)
per_file = defaultdict(list)
for (tp, q), n in def_in.items():
    per_file[tp].append((n, q, len(def_callers[(tp, q)])))
for p in nodes:
    nodes[p]["hot"] = [{"name": q, "calls": n, "files": f} for n, q, f in sorted(per_file[p], reverse=True)[:8]]
    nodes[p]["doc"] = ""
    mod = index.files[p]["py"]
    # first docstring line of the module, if the record keeps units
    for u in index.files[p].get("units", []):
        if isinstance(u, list) and len(u) > 5 and u[1] == "module":
            nodes[p]["doc"] = (u[5] or "").strip().splitlines()[0][:160] if (u[5] or "").strip() else ""
            break

head = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%h %s"], capture_output=True, text=True).stdout.strip()
branch = subprocess.run(["git", "-C", repo, "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
st = ci.stats(index)
data = {"repo": "lihowfun/O-ALL-WANT", "branch": branch, "commit": head, "stats": {k: st[k] for k in ("symbols", "imports", "calls") if k in st},
        "file_counts": st.get("files"), "resolved_calls": resolved, "unresolved_calls": unresolved,
        "nodes": sorted(nodes.values(), key=lambda n: n["id"]), "links": sorted(links.values(), key=lambda l: (l["source"], l["target"])), "hubs": hubs}
with open(out, "w", encoding="utf-8") as h:
    json.dump(data, h, ensure_ascii=False, separators=(",", ":"))
print("nodes", len(nodes), "links", len(links), "import pairs", len(imp), "call pairs", len(calls), "resolved", resolved, "unresolved", unresolved)
print("groups", Counter(n["group"] for n in nodes.values()))
print("top hubs", [(h["file"].split("/")[-1], h["name"], h["calls"]) for h in hubs[:12]])
print(json.dumps(st, ensure_ascii=False)[:600])
