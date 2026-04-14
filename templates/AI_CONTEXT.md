# ${PROJECT_NAME} — AI Agent Context (Project Facts SSOT)

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
- Keep routing, forbidden actions, and end-of-task reporting rules in
  `CLAUDE.md`. Do not turn this file into a second router.

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

## Critical Project Facts

- Safety-critical file: `${SAFETY_CRITICAL_FILE}`
- Workaround that must be preserved: `${IMPORTANT_WORKAROUND}`
- Behavioral rules, startup routing, and forbidden actions live in `CLAUDE.md`

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

## Information Surfaces

| Surface | Primary Files | What Lives There |
|---------|---------------|------------------|
| Operational | `AI_CONTEXT.md`, `ROADMAP.md`, `VERSION.json`, `.agents/memory.md` | Current state, guardrails, recent decisions |
| Wiki | `docs/knowledge/index.md`, topic pages, `Experiment_Findings.md` | Durable background knowledge and reusable findings |
| Execution | `.agents/skills/*.md`, `scripts/*.py` | Repeatable workflows and deterministic maintenance |
| Raw fallback | `docs/raw/*.md` | Detailed source notes used only when a compiled topic is missing or stale |

## Concrete Commands

- Smoke test: `${SMOKE_TEST_CMD}`
- Regression test: `${REGRESSION_TEST_CMD}`
- Integration test: `${INTEGRATION_TEST_CMD}`
- Refresh one wiki topic: `python3 scripts/wiki_sync.py refresh ${PRIMARY_WIKI_TOPIC}`
- Lint wiki metadata: `python3 scripts/wiki_sync.py lint`
