---
name: wiki-refresh
description: "Refresh a compiled wiki topic from docs/raw/ and verify the result"
triggers: ["refresh wiki", "update knowledge", "rebuild topic"]
params:
  TOPIC: "target wiki topic id"
requires:
  - AI_CONTEXT.md
  - VERSION.json
optional_reads:
  - docs/raw/${TOPIC}.md
outputs:
  - .agents/memory.md entry
---

# /wiki-refresh — Refresh Topic

1. Read the matching raw source note in `docs/raw/`
2. Run `python3 scripts/wiki_sync.py refresh ${TOPIC}`
3. Run `python3 scripts/wiki_sync.py lint`
4. Record the refresh in `.agents/memory.md`
