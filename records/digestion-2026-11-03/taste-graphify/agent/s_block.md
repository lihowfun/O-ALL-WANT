
## OAW code index

This project has a regenerable code index, `scripts/code_index.py` (standard library only), that knows every definition, import and call site.

Rules:
- For a codebase question, run `python3 scripts/code_index.py find "<question>"` before your first grep, search or source-file read. Read raw files only for lines the index or an earlier read already located.
- Use `python3 scripts/code_index.py callers <symbol>` for who calls a function, `python3 scripts/code_index.py path <A> <B>` for how one module reaches another, and `python3 scripts/code_index.py affected <file or symbol>` for what a change touches.
- The index is rebuilt on each call from the source; there is nothing to update.
