# Minimal Example App — AI Agent Context (Single Source of Truth)

> Post-install sample project for validating the Agent Memory Framework |
> 0.1.0-example | Repo: https://github.com/lihowfun/agent-memory-framework
> Pipeline: **Install framework -> run CLI smoke tests -> document findings**

## Language

- Discussion: **English**. Professional terms keep English.
- Code / docstrings / commit messages: English

## Architecture

```
README.md ───────────────→ onboarding + validation steps
ROADMAP.md ──────────────→ current release tasks
scripts/context_hub.py ──→ optional CLI for memory + knowledge management
.agents/memory.md ───────→ rolling decision log
docs/knowledge/*.md ─────→ permanent project knowledge
.agents/skills/*.md ─────→ reusable workflows for common tasks
```

## Core Rules

1. Back decisions with data — don't be a yes-man
2. Act first, ask later — prove with experiments
3. Add only, don't delete (unless explicitly asked)
4. Explain in plain language — no jargon without context
5. End every task with a report — **4-section format enforced** (What / Verified / Docs updated / Next). See `CLAUDE.md ## Session End`

## Forbidden Actions

- Do not modify `scripts/context_hub.py` without rerunning the smoke commands
- Do not remove the `python3` examples until the target machine is verified to
  provide a working `python` alias
- Do not re-run experiments listed in `VERSION.json` `do_not_rerun`
- Do not hardcode credentials (use env vars)

## Current Baselines

| Metric | Value | Date | Notes |
|--------|-------|------|-------|
| Clone + install + first status | 3.55s | 2026-04-13 | Measured in a fresh macOS fixture |
| Install only | 0.04s | 2026-04-13 | Same fixture, local framework copy |

## Testing

| Tier | When | Command |
|------|------|---------|
| 1 Smoke | After code change | `python3 scripts/context_hub.py status` |
| 2 Regression | After CLI/doc changes | `python3 scripts/context_hub.py search "" && python3 scripts/context_hub.py memory show --last 3` |
| 3 Integration | Before release | `python3 scripts/context_hub.py bootstrap` |

## Tech Stack

- Markdown templates + Python 3 CLI
- Local filesystem only
- No external services required

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
