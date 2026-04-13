# ${PROJECT_NAME} — AI Agent Context (Single Source of Truth)

> ${ONE_LINE_DESCRIPTION} | ${VERSION} | Repo: ${REPO_URL}
> Pipeline: **${PIPELINE_SUMMARY}**

## Language

- Discussion: **${LANGUAGE}**. Professional terms keep English.
- Code / docstrings / commit messages: English

## Architecture

<!-- Draw your project's architecture here -->
```
entry_point ─┬─→ module_a        Description
             ├─→ module_b        Description
             ├─→ module_c        Description
             └─→ module_d        Description
```

## Core Rules

1. Back decisions with data — don't be a yes-man
2. Act first, ask later — prove with experiments
3. Add only, don't delete (unless explicitly asked)
4. Explain in plain language — no jargon without context
5. End every task with a report — **4-section format enforced** (What / Verified / Docs updated / Next). See `CLAUDE.md ## Session End`

## Forbidden Actions

<!-- Project-specific things that should never be modified -->
- Do not modify `${SAFETY_CRITICAL_FILE}`
- Do not remove `${IMPORTANT_WORKAROUND}`
- Do not re-run experiments listed in `VERSION.json` `do_not_rerun`
- Do not hardcode credentials (use env vars)

## Current Baselines

<!-- Track your key metrics here. Update when you achieve new bests. -->

| Metric | Value | Date | Notes |
|--------|-------|------|-------|
| ${METRIC_1} | ${VALUE_1} | ${DATE} | ${NOTES} |
| ${METRIC_2} | ${VALUE_2} | ${DATE} | ${NOTES} |

## Testing

| Tier | When | Command |
|------|------|---------|
| 1 Smoke | After code change | `${SMOKE_TEST_CMD}` |
| 2 Regression | After algorithm change | `${REGRESSION_TEST_CMD}` |
| 3 Integration | Before release | `${INTEGRATION_TEST_CMD}` |

## Tech Stack

- ${LANGUAGE_AND_FRAMEWORKS}
- ${RUNTIME_ENVIRONMENT}
- ${EXTERNAL_SERVICES}

## Key Files — Lazy Read Protocol

> ⚠️ Don't read everything at once! Read on demand based on the current task.
> Full routing table: see `CLAUDE.md`.

| Priority | File | When to Read | Lines |
|:--------:|------|-------------|:-----:|
| 🔴 Must | `AI_CONTEXT.md` (this file) | Every session | ~100 |
| 🔴 Must | `VERSION.json` (version + do_not_rerun) | Every session | ~20 |
| 🟡 On demand | `ROADMAP.md` first 60 lines | Changing code / running experiments | varies |
| 🟡 On demand | `.agents/memory.md` last 5 entries | Checking past decisions | varies |
| 🟡 On demand | `docs/knowledge/*.md` | By topic | 30-90 each |
| 🚫 Never | `docs/archive/*` | Stale, retired docs | — |
