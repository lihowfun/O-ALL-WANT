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
outputs:
  - .agents/memory.md entry
  - docs/knowledge/${TOPIC}.md annotation (if significant)
---

# /${SKILL_NAME} — ${SHORT_TITLE}

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
python scripts/context_hub.py memory add "[TAG] ${SKILL_NAME} — ${SUMMARY}"
```

If significant finding:
```bash
python scripts/context_hub.py annotate ${TOPIC} "[TAG] ${FINDING}"
```

---

## Edge Cases (Learning Block)

> Auto-appended when anomalies occur during execution.

<!-- 
- [YYYY-MM-DD] Description of edge case and resolution
-->
