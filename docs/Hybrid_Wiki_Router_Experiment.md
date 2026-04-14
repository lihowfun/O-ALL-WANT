# Hybrid Wiki Router Experiment

This document records the experimental branch implementation for the hybrid
wiki router.

## Recommendation

Do not replace the current framework with a pure LLM Wiki. Keep three lanes:

- **Operational lane**: `AI_CONTEXT.md`, `ROADMAP.md`, `VERSION.json`, recent `.agents/memory.md`
- **Wiki lane**: `docs/knowledge/*.md`, `index.md`, `log.md`
- **Execution lane**: `.agents/skills/*.md`

`docs/raw/` is the fallback-only source layer that feeds the compiled wiki.

## What Changed In This Branch

- Added `scripts/wiki_sync.py`
- Added `docs/raw/` starter templates
- Upgraded knowledge pages to use frontmatter metadata
- Added `Experiment_Findings.md`, `index.md`, and `log.md`
- Added `wiki-refresh.md` skill
- Added a public hybrid demo example

## Verification Snapshot

- `python3 -m py_compile scripts/context_hub.py scripts/wiki_sync.py`
- `python3 example/public-hybrid-demo/scripts/wiki_sync.py build`
- `python3 example/public-hybrid-demo/scripts/wiki_sync.py lint`
- `python3 example/public-hybrid-demo/scripts/context_hub.py status`
- `python3 example/public-hybrid-demo/scripts/context_hub.py search "router"`
- `python3 example/public-hybrid-demo/scripts/context_hub.py annotate Experiment_Findings "..."`
- `python3 example/public-hybrid-demo/scripts/wiki_sync.py refresh Experiment_Findings`
- fresh install smoke in an empty temp directory:
  - `bash install.sh`
  - `python3 scripts/context_hub.py status`
  - `python3 scripts/wiki_sync.py lint`

Observed result:

- Example build/lint passed
- Annotation persistence now survives wiki refreshes
- Fresh install + first status + lint completed successfully in under one second on the local machine
- Default starter still works even before any real raw source notes are added

## Experiment Modes

### A. Current baseline

- Operational docs + rolling memory + skills
- No wiki compiler

### B. Wiki-heavy

- Raw sources + compiled wiki + schema routing
- Minimal recent-memory usage

### C. Hybrid-router

- Operational docs for active state
- Compiled wiki for durable knowledge
- Skills for execution

## Prompt Suite

Use the same prompts across all three modes:

1. Onboard a new agent into the repo
2. Recall a prior decision and explain why it was made
3. Answer a durable background question from project docs
4. Update knowledge after a new raw source note is added
5. Plan around current phase or release status

## Merge Criteria

- Default install still feels simple without using wiki sync on day one
- Router chooses the right lane on at least 90% of the prompt suite
- Topic refresh touches only the target page plus `index.md` and `log.md`
- `python3 scripts/wiki_sync.py lint` passes on the public demo
- Hybrid mode matches or beats the baseline on long-horizon consistency

## Current Recommendation

Merge the hybrid-router path only if it wins on consistency and update
efficiency without hurting onboarding. Keep the pure wiki-heavy path as an
experiment unless it clearly outperforms the hybrid model.

Current branch read:

- keep the hybrid router as the recommended next version
- keep wiki sync optional in the default onboarding path
- use the public hybrid demo as the public reference implementation
