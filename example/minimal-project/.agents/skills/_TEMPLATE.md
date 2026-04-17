---
name: skill-template
description: "${ONE_SENTENCE_DESCRIPTION}"
triggers: ["${KEYWORD_1}", "${KEYWORD_2}", "${KEYWORD_3}"]
params:
  PARAM1: "${DESCRIPTION} | ${ALLOWED_VALUES}"
  PARAM2: "${DESCRIPTION}"
requires:
  - AI_CONTEXT.md
  - VERSION.json
optional_reads:
  - docs/knowledge/${RELEVANT_TOPIC}.md
  - docs/raw/${OPTIONAL_SOURCE}.md
outputs:
  - .agents/memory.md entry
  - docs/knowledge/${TOPIC}.md annotation (if significant)
---

# /${SKILL_NAME} — ${SHORT_TITLE}

> Replace every `${...}` token before first use. Parameter placeholders should
> match the `params` block above; any extra runtime placeholders should be
> explained inline for the next person reading the skill.
> If the skill refreshes compiled wiki pages, call `python3 scripts/wiki_sync.py`
> after editing `docs/raw/`.

## Parameters
- **PARAM1**: ${PARAM1}
- **PARAM2**: ${PARAM2}

## Steps

### Step 1: Pre-checks
- [ ] ${PRECONDITION_1}
- [ ] ${PRECONDITION_2}
- [ ] Read `VERSION.json` → confirm not in `do_not_rerun`

### Step 2: Execute Core Action

${INSTRUCTIONS_OR_COMMANDS}

### Step 3: Verify Results

${HOW_TO_CONFIRM_SUCCESS}

### Step 4: Record Results

```bash
python3 scripts/context_hub.py memory add "[TAG] ${SKILL_NAME} — ${SUMMARY}"
```

If significant finding:
```bash
python3 scripts/context_hub.py annotate ${TOPIC} "[TAG] ${FINDING}"
```

If the skill changes `docs/raw/`:
```bash
python3 scripts/wiki_sync.py refresh ${TOPIC}
python3 scripts/wiki_sync.py lint
```

---

## Edge Cases (Learning Block)

> Auto-appended when anomalies occur during execution.

<!-- 
- [YYYY-MM-DD] Description of edge case and resolution
-->
