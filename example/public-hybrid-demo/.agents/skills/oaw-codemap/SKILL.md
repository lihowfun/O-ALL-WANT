---
name: oaw-codemap
description: Draw offline dependency maps and find callers, affected files, import paths and a one-page overview of this repository with OAW's code index. Results are pointers to read, not facts.
disable-model-invocation: true
---

# OAW code map

Run from the project root with Python 3.10+ (`py -3` on Windows if needed):

```bash
python3 scripts/code_index.py graph --scope src --out map.html  # offline drawing; open locally
python3 scripts/code_index.py graph --scope src --format mermaid  # small diagram for context
python3 scripts/code_index.py overview                    # one page: entry points, main modules, most-called definitions
python3 scripts/code_index.py callers PATH::NAME          # call sites (Python, JavaScript, TypeScript)
python3 scripts/code_index.py affected PATH[::NAME] --hops 2
python3 scripts/code_index.py find "free-text description"
python3 scripts/code_index.py path A.py B.py               # import chain between two modules
```

- Use it to decide where to read: callers and impact first; `overview` in an unfamiliar repository. Skip it in a
  small repository or when you already know the file.
- Text query results are pointers: `file:line` and one line of source. Read those lines before you state what the code
  does, and describe behavior from what you read, not from this output.
- "complete within the index" means every indexed match came back, within the languages and hops it tracks.
  Calls on receivers of unknown type are listed apart. Dynamic dispatch, string-named calls, reflection and
  dependency injection are not followed.
- The cache lives in your user cache folder, outside the project; `--no-cache` skips it.
- `graph` reuses the index: files grouped by directory, arrows to dependencies, weight = import bindings +
  resolved call sites. HTML has search, neighbor highlighting and top callers/callees; no network or CDN.
  Graphs include tests and isolated Python/JS/TS files; external, unresolved and intra-file edges are omitted.
- `--scope DIR` keeps both endpoints inside that directory. `--format json` exposes the same graph data.
  Caps default to 200 nodes/500 edges (Mermaid: 40/80); `--max-nodes` and `--max-edges` accept 1–1000.
  Read `complete`, `truncated`, totals and limits before claiming coverage. Lists describe displayed edges.
  Use a smaller scope when truncated; nodes rank by total incident edge weight, with path tie-breaks.
  Exported paths and structure may be private; review before sharing. No agent comprehension benefit is measured.
