# Public Hybrid Demo — AI Agent Context

> Public hybrid wiki router demo | 0.2.0-example | Repo: https://github.com/lihowfun/agent-memory-framework
> Pipeline: **Raw notes -> compiled wiki -> reusable project knowledge**

## Language

- Discussion: **English**
- Code / docstrings / commit messages: English

## Architecture

```text
ROADMAP.md / VERSION.json ─────→ phase, experiment guardrails, do_not_rerun
.agents/memory.md ─────────────→ recent decisions and findings
docs/raw/*.md ─────────────────→ fallback-only source notes
docs/knowledge/*.md ───────────→ compiled durable wiki pages
.agents/skills/*.md ───────────→ execution workflows
```

## Core Rules

1. Read `AI_CONTEXT.md` and `VERSION.json` first
2. Use the operational lane for current state and release scope
3. Use the compiled wiki before touching `docs/raw/`
4. Use `docs/raw/` only when a topic is missing or stale
5. End substantial tasks with a report plus a memory update

## Forbidden Actions

- Do not edit generated wiki pages directly when the topic has a matching raw source
- Do not re-run experiments in `VERSION.json` `do_not_rerun`
- Do not hardcode secrets

## Current Baselines

| Metric | Value | Date | Notes |
|--------|-------|------|-------|
| Router evaluation coverage | 5 prompts | 2026-04-13 | Baseline suite for A/B/C comparison |
| Default install promise | < 1 minute | 2026-04-13 | Wiki sync remains optional |

## Testing

| Tier | When | Command |
|------|------|---------|
| 1 Smoke | After docs or script changes | `python3 scripts/context_hub.py status` |
| 2 Wiki Integrity | After raw/wiki changes | `python3 scripts/wiki_sync.py build && python3 scripts/wiki_sync.py lint` |
| 3 Integration | Before release recommendation | `python3 scripts/context_hub.py bootstrap` |

## Tech Stack

- Markdown docs + Python 3 helper scripts
- Local files only
- No external services or vector databases

## Context Lanes

| Lane | Primary Files | Use For |
|------|---------------|---------|
| Operational | `AI_CONTEXT.md`, `ROADMAP.md`, `VERSION.json`, `.agents/memory.md` | Phase status, current priorities, release rules |
| Wiki | `docs/knowledge/index.md`, topic pages, `Experiment_Findings.md` | Durable background knowledge |
| Execution | `.agents/skills/*.md` | Repeated workflows such as wiki refresh or experiment reporting |

## Raw Source Rule

If a topic is missing or stale:

1. read the matching file in `docs/raw/`
2. run `python3 scripts/wiki_sync.py refresh <topic>`
3. run `python3 scripts/wiki_sync.py lint`
