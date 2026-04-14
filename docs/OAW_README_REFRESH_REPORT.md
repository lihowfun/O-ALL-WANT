# OAW README Refresh Report

> Date: 2026-04-14
> Branch: `codex/oaw-readme-zh`

## What Changed

- Rewrote the homepage README into a Chinese-first `O-ALL-WANT (OAW)` landing page.
- Added a simple architecture diagram that makes `CLAUDE.md` the visible master router.
- Put the design lineage back on the homepage with direct links to the upstream inspirations.
- Reduced template rule duplication so `CLAUDE.md` owns behavior and `AI_CONTEXT.md` owns project facts.
- Updated internal docs so the startup story no longer conflicts with the new README.
- Fixed a brittle `wiki_sync.py lint` stale-page check so it uses raw-note metadata
  instead of filesystem checkout times.

## What Problem Was Being Fixed

Before this refresh, the public `main` branch had three presentation problems:

1. The homepage looked too flat and undersold the integrated architecture.
2. The source lineage still existed in `docs/Architecture_Origins.md`, but it was effectively invisible from the homepage.
3. `CLAUDE.md` and `AI_CONTEXT.md` both carried too much control language, which made the router design harder to explain and slightly increased rule-weight dilution risk.

## Is The Rule-Conflict Risk Solved?

**Reduced significantly, not magically eliminated.**

What is better now:

- `CLAUDE.md` is explicitly the only startup router.
- `AI_CONTEXT.md` now behaves more like a facts-and-commands sheet than a second policy file.
- Repeated procedures are pointed toward skills and scripts instead of extra prose.
- The README now explains that wiki maintenance is invoked, not always-on.

Residual risk that still exists:

- A team can still overstuff `AI_CONTEXT.md` with too many project-specific rules.
- A project can still create too many skills or too many always-read files if it ignores the lazy-read design.
- Human maintainers can still drift from the template if they keep adding policy in multiple places.

Recommended long-term guardrail:

- Keep `CLAUDE.md` for routing and behavior.
- Keep `AI_CONTEXT.md` for facts, baselines, environment, and commands.
- Move repeatable procedure into skills or scripts instead of more markdown policy.

## How It Was Verified

### Public smoke gate

- `python3 -m py_compile scripts/context_hub.py scripts/wiki_sync.py`
- `python3 example/public-hybrid-demo/scripts/wiki_sync.py build`
- `python3 example/public-hybrid-demo/scripts/wiki_sync.py lint`
- `python3 example/public-hybrid-demo/scripts/context_hub.py status`

### Template regression

- Ran a fresh install smoke test in a temporary empty project using `install.sh`
- Confirmed the generated repo still exposes `CLAUDE.md`, `AI_CONTEXT.md`, `VERSION.json`, `ROADMAP.md`, `scripts/context_hub.py`, and `scripts/wiki_sync.py`

### Manual doc checks

- Confirmed the README contains a top-level architecture diagram
- Confirmed the README source lineage section explicitly names:
  - `context-hub`
  - `MemPalace`
  - Garry Tan / thin harness, fat skills
  - Karpathy-style LLM Wiki
- Confirmed the internal docs no longer present a conflicting startup story

## Conclusion

The core architecture did not need a rewrite.

The bigger issue was that the public presentation hid the architecture’s strengths
and the template wording made the router split less obvious than it should have
been. This refresh keeps the same underlying design, but makes the intended
operating model much easier for both humans and agents to follow.
