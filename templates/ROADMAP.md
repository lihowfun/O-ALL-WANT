# ROADMAP

Use this file as the short operational plan for the repo. Keep the first
60 lines current, because the lazy-read protocol points agents here when they
need to understand phase status or execution priorities.

## Current Focus

- Phase: Foundation
- Goal: Finish initial setup and first smoke test
- Definition of done: Install flow works, core docs are filled in, first example
  project is runnable, and optional wiki sync passes lint

## Active Work

| Priority | Workstream | Status | Notes |
|----------|------------|--------|-------|
| P0 | Install + onboarding | In progress | Validate fresh-project setup and fix blockers |
| P1 | Operational docs | Planned | Fill AI context, roadmap, version metadata |
| P1 | Wiki layer | Planned | Add source notes under `docs/raw/`, compile durable pages |
| P2 | Release readiness | Planned | Beta feedback, launch checklist, public announcement |

## Next Milestones

1. Confirm the install flow in an empty project.
2. Fill in `AI_CONTEXT.md`, `CLAUDE.md`, and `VERSION.json`.
3. Add one real project-specific skill.
4. Add one real raw source note and run `python3 scripts/wiki_sync.py build`.
5. Record the first significant decision in `.agents/memory.md`.

## Completed

- Framework files installed
- Knowledge topics bootstrapped
