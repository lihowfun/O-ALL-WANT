---
name: oaw-codemap
description: Find callers, affected files, import paths and a one-page overview of this repository with OAW's code index. Results are pointers to read, not facts.
disable-model-invocation: true
---

# OAW code map

Run from the project root with Python 3.10+ (`py -3` on Windows if needed):

```bash
python3 scripts/code_index.py overview                    # one page: entry points, main modules, most-called definitions
python3 scripts/code_index.py callers PATH::NAME          # call sites (Python, JavaScript, TypeScript)
python3 scripts/code_index.py affected PATH[::NAME] --hops 2
python3 scripts/code_index.py find "free-text description"
python3 scripts/code_index.py path A.py B.py               # import chain between two modules
```

- Use it to decide where to read: callers and impact first; `overview` in an unfamiliar repository. Skip it in a
  small repository or when you already know the file.
- Every result is a pointer: `file:line` and one line of source. Read those lines before you state what the code
  does, and describe behavior from what you read, not from this output.
- "complete within the index" means every indexed match came back, within the languages and hops it tracks.
  Calls on receivers of unknown type are listed apart. Dynamic dispatch, string-named calls, reflection and
  dependency injection are not followed.
- The cache lives in your user cache folder, outside the project; `--no-cache` skips it.
