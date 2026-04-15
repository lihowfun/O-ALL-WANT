# Raw Sources

`docs/raw/` stores sanitized source material that feeds the compiled wiki.

Rules:

- Keep raw files immutable in spirit: add new notes or append clearly dated
  updates instead of silently rewriting history.
- Do **not** make agents read every raw file at startup.
- Refresh compiled pages with `python3 scripts/wiki_sync.py build` or
  `python3 scripts/wiki_sync.py refresh <topic>`.
- Run `python3 scripts/wiki_sync.py lint` after changing source notes.

Start from `_SOURCE_TEMPLATE.md` when adding a new source note.
