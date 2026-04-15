---
name: wiki-refresh
description: "Refresh a compiled wiki topic from docs/raw/ and verify the result"
triggers: ["refresh wiki", "update knowledge", "rebuild topic", "wiki sync"]
params:
  TOPIC: "topic id in docs/knowledge/ and docs/raw/"
requires:
  - AI_CONTEXT.md
  - VERSION.json
optional_reads:
  - docs/knowledge/index.md
  - docs/raw/${TOPIC}.md
outputs:
  - .agents/memory.md entry
  - docs/knowledge/${TOPIC}.md refresh
---

# /wiki-refresh — Refresh Compiled Wiki Topic

## Parameters
- **TOPIC**: Topic ID that should be rebuilt from `docs/raw/`

## Steps

### Step 1: Confirm the source of truth
- [ ] Read `docs/knowledge/index.md` to confirm the topic exists or should exist
- [ ] Read `docs/raw/` source notes for the target topic
- [ ] Confirm the topic is not blocked by `VERSION.json` `do_not_rerun`

### Step 2: Refresh the topic

```bash
python3 scripts/wiki_sync.py refresh ${TOPIC}
```

### Step 3: Verify integrity

```bash
python3 scripts/wiki_sync.py lint
python3 scripts/context_hub.py get ${TOPIC}
```

### Step 4: Record results

```bash
python3 scripts/context_hub.py memory add "[DECISION] Refreshed wiki topic ${TOPIC} from docs/raw/"
```

If the refresh introduced a new reusable finding:

```bash
python3 scripts/context_hub.py annotate ${TOPIC} "[INSIGHT] Refreshed compiled wiki after source update"
```

---

## Edge Cases (Learning Block)

> Auto-appended when anomalies occur during execution.

<!--
- [YYYY-MM-DD] Refresh failed because a manual page used the same topic id. Rename the raw topic or migrate the page metadata first.
-->
