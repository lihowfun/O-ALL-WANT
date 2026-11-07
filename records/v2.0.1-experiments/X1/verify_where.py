"""Mechanical check of reference facts: every `where` file exists, every symbol resolves (Python via ast, JS by a
definition pattern), and every code-like name quoted in a fact occurs in one of its cited files (else repo-wide).
    python3 verify_where.py <repo root> <questions.json> [<json report>]"""
import ast, json, os, re, subprocess, sys

root, qpath = sys.argv[1], sys.argv[2]
out = sys.argv[3] if len(sys.argv) > 3 else None
_trees = {}

def tree(path):
    if path not in _trees:
        _trees[path] = ast.parse(open(path, encoding="utf-8").read())
    return _trees[path]

def py_resolve(path, dotted):
    nodes = tree(path).body
    for part in dotted.split("."):
        found = None
        for n in nodes:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == part:
                found = n
                break
            if isinstance(n, (ast.Assign, ast.AnnAssign)):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                if any(isinstance(t, ast.Name) and t.id == part for t in targets):
                    found = n
                    break
        if found is None:
            # nested defs inside if/try blocks at this level
            for n in nodes:
                for sub in ast.walk(n):
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and sub.name == part:
                        found = sub
                        break
                if found:
                    break
        if found is None:
            return None
        nodes = getattr(found, "body", [])
    return found

def js_resolve(path, name):
    text = open(path, encoding="utf-8").read()
    last = re.escape(name.split(".")[-1])
    pats = [rf"\b{last}\s*:\s*(async\s+)?function\b", rf"\b{last}\s*:\s*(async\s*)?\(", rf"\bfunction\s+{last}\s*\(",
            rf"\b{last}\s*=\s*(async\s+)?function\b", rf"\b{last}\s*=\s*(async\s*)?\(", rf"^\s*(async\s+)?{last}\s*\([^)]*\)\s*\{{",
            rf"\b{last}\s*\([^)]*\)\s*\{{", rf"\b{last}\s*:\s*\w"]
    if "." in name and name not in text:
        return False
    return any(re.search(p, text, re.M) for p in pats)

CODE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b|\b[a-z][a-z0-9]*_[a-z0-9_]+\b|\b[A-Z][a-z]+[A-Z][A-Za-z]+\b")
SKIP = {"e.g", "i.e"}
problems, checked, names_checked = [], 0, 0
repo_files_cache = {}

def in_repo(token):
    if token in repo_files_cache:
        return repo_files_cache[token]
    r = subprocess.run(["grep", "-rlF", "--include=*.py", "--include=*.js", "--include=*.json", "--include=*.html", token, root],
                       capture_output=True, text=True)
    repo_files_cache[token] = [os.path.relpath(p, root) for p in r.stdout.split()][:3]
    return repo_files_cache[token]

for q in json.load(open(qpath, encoding="utf-8"))["questions"]:
    for f in q["facts"]:
        texts = []
        for loc in [x.strip() for x in f["where"].split(";") if x.strip()]:
            checked += 1
            path, _, sym = loc.partition("::")
            full = os.path.join(root, path)
            if not os.path.isfile(full):
                problems.append({"fact": f["id"], "where": loc, "problem": "file missing"}); continue
            texts.append(open(full, encoding="utf-8").read())
            if not sym:
                problems.append({"fact": f["id"], "where": loc, "problem": "no symbol"}); continue
            ok = py_resolve(full, sym) is not None if path.endswith(".py") else js_resolve(full, sym)
            if not ok:
                problems.append({"fact": f["id"], "where": loc, "problem": "symbol not defined"})
        blob = "\n".join(texts)
        for token in sorted(set(CODE.findall(f["fact"]))):
            if token in SKIP or re.fullmatch(r"[A-Za-z]+\.(py|js|json)", token):
                continue
            names_checked += 1
            parts = token.split(".")
            # dotted module paths: the last part must occur; plain names: the name itself
            probe = token if "." not in token else parts[-1]
            if token.endswith((".py", ".js")):
                probe = token.rsplit("/", 1)[-1]
            if probe in blob or token in blob:
                continue
            hits = in_repo(probe)
            problems.append({"fact": f["id"], "token": token, "problem": "name not in cited files",
                             "found_elsewhere": hits})
report = {"locations": checked, "names": names_checked, "problems": problems}
print(json.dumps(report, indent=1))
if out:
    json.dump(report, open(out, "w"), indent=1)
