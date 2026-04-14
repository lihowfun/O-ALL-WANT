# Research Pipeline Demo — Agent Rules

## Response Language

- English is the default
- Keep technical terms in English

## Session Startup

Always read:

1. `AI_CONTEXT.md`
2. `VERSION.json`

Then route by lane:

| Task | Read Next | Avoid |
|------|-----------|-------|
| Branch / merge status | `BRANCH.md`, `BRANCH_STATUS.md`, `ROADMAP.md` | Raw source notes |
| Durable background question | `docs/knowledge/index.md` + relevant topic page | Reading all topic pages |
| Repeated workflow | matching skill in `.agents/skills/` | Inventing new SOPs |
| Missing or stale topic | matching `docs/raw/*.md` + `scripts/wiki_sync.py` | Editing compiled page directly |

## File Map

```text
AI_CONTEXT.md        strong SSOT
ROADMAP.md           current phase and priorities
VERSION.json         version + do_not_rerun + benchmark snapshot
BRANCH.md            branch scope and merge gates
BRANCH_STATUS.md     current experimental status
.agents/memory.md    recent decision log
docs/raw/            fallback-only source notes
docs/knowledge/      compiled durable wiki
.agents/skills/      execution workflows
scripts/             thin deterministic helpers
```

## Mandatory Wrap-Up

Every substantial task must include:

1. What changed
2. How it was verified
3. Which docs were updated
4. What comes next

## Forbidden Actions

1. Do not read every markdown file at startup
2. Do not edit generated wiki pages directly when a raw source exists
3. Do not re-run blocked experiments
4. Do not delete branch docs until the experiment is either merged or retired
