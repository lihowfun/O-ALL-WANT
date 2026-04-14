# ${PROJECT_NAME} — AI Agent Context (Single Source of Truth)

> ${ONE_LINE_DESCRIPTION} | ${VERSION} | Repo: ${REPO_URL}
> Pipeline: **${PIPELINE_SUMMARY}**

## Customize This File

- Replace `${PROJECT_NAME}`, `${ONE_LINE_DESCRIPTION}`, `${VERSION}`, `${REPO_URL}`,
  and `${PIPELINE_SUMMARY}` with your project identity and deployment summary.
- Replace `${LANGUAGE}` with your preferred discussion language.
- Replace `${SAFETY_CRITICAL_FILE}` and `${IMPORTANT_WORKAROUND}` with the
  highest-risk file and workaround that agents must preserve.
- Replace the metric placeholders (`${METRIC_1}`, `${VALUE_1}`, `${NOTES}`, etc.)
  with the baselines you actually track.
- Replace `${SMOKE_TEST_CMD}`, `${REGRESSION_TEST_CMD}`, and
  `${INTEGRATION_TEST_CMD}` with copy-pasteable commands from your repo.
- Replace `${LANGUAGE_AND_FRAMEWORKS}`, `${RUNTIME_ENVIRONMENT}`, and
  `${EXTERNAL_SERVICES}` with your real stack.
- If you keep `docs/raw/` source notes, replace the example sync commands and
  topic names with the actual wiki topics your project uses.

## Language

- Discussion: **${LANGUAGE}**. Professional terms keep English.
- Code / docstrings / commit messages: English

## Architecture

<!-- Draw your project's architecture here -->
```
                      ┌──────────────────────────────┐
                      │  Operational Lane            │
                      │  AI_CONTEXT / ROADMAP /      │
                      │  VERSION / recent memory     │
                      └──────────────┬───────────────┘
                                     │
                                     │ choose by task
                                     ▼
┌─────────────────────┐     ┌──────────────────────────────┐     ┌─────────────────────┐
│  docs/raw/          │────▶│  Compiled Wiki Lane          │◀────│  .agents/skills/    │
│  Source notes       │     │  docs/knowledge/*.md         │     │  Execution lane     │
│  fallback only      │     │  + index.md + log.md         │     │  reusable workflows │
└─────────────────────┘     └──────────────────────────────┘     └─────────────────────┘
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
- Do not treat `docs/raw/` as startup-default context
- Do not edit compiled wiki pages directly if the same topic is generated from `docs/raw/`

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

## Context Lanes

| Lane | Primary Files | Use For | Avoid |
|------|---------------|---------|-------|
| Operational | `AI_CONTEXT.md`, `ROADMAP.md`, `VERSION.json`, `.agents/memory.md` | Branch status, release planning, active experiments | Reading all knowledge pages up front |
| Wiki | `docs/knowledge/index.md`, topic pages, `Experiment_Findings.md` | Stable concepts, reusable findings, durable background | Jumping straight to raw sources |
| Execution | `.agents/skills/*.md` | Repeated workflows with verification steps | Re-inventing the same SOP ad hoc |

## Knowledge Sync Rules

- `docs/raw/` stores sanitized source material and is **fallback-only**
- `docs/knowledge/` stores durable compiled pages meant for normal retrieval
- If a topic is missing or stale, refresh it with:
  - `python3 scripts/wiki_sync.py refresh ${PRIMARY_WIKI_TOPIC}`
  - `python3 scripts/wiki_sync.py lint`

## Key Files — Lazy Read Protocol

> ⚠️ Don't read everything at once! Read on demand based on the current task.
> Full routing table: see `CLAUDE.md`.

| Priority | File | When to Read | Lines |
|:--------:|------|-------------|:-----:|
| 🔴 Must | `AI_CONTEXT.md` (this file) | Every session | ~100 |
| 🔴 Must | `VERSION.json` (version + do_not_rerun) | Every session | ~20 |
| 🟡 On demand | `ROADMAP.md` first 60 lines | Changing code / running experiments | varies |
| 🟡 On demand | `.agents/memory.md` last 5 entries | Checking past decisions | varies |
| 🟡 On demand | `docs/knowledge/index.md` + topic pages | Stable background / reusable findings | 20-120 each |
| 🟡 Fallback | `docs/raw/*.md` | Topic missing or stale in compiled wiki | varies |
| 🟡 Tooling | `scripts/wiki_sync.py` | Rebuild / lint compiled wiki | ~150 |
| 🚫 Never | `docs/archive/*` | Stale, retired docs | — |
