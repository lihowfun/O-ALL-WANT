# Agent Memory Framework — AI Agent Context

> ⚠️ **FORBIDDEN**: Do NOT put agent operational instructions here. Use `CLAUDE.md` instead.

> AI Agent 的長期記憶與知識管理框架 | dev | Repo: lihowfun/O-ALL-WANT  
> Pipeline: **Template repo → install.sh → Per-project harness**

## Language

- Discussion: **繁體中文**. Professional terms keep English.
- Code / docstrings / commit messages: English

## Architecture

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

- **Safety-critical file**: `install.sh` — installer script, affects all users
- **Key invariants**:
  - `templates/` and `example/minimal-project/` must stay in sync
  - `scripts/context_hub.py` and `scripts/wiki_sync.py` are framework core
  - Skills and knowledge live in `templates/` only (no root duplicates)
- **Self-hosting**: This repo manages itself with its own harness.
  Root `CLAUDE.md`/`AI_CONTEXT.md` are customized for OAW development.
  `templates/` holds the user-facing placeholders.
- **Behavioral rules**: Live in `CLAUDE.md`, not here

## Current Baselines

| Metric | Value | Date | Notes |
|--------|-------|------|-------|
| Install time | < 5s | 2026-04-14 | Fresh install on macOS |
| Template file count | 15 | 2026-04-14 | Core harness files |
| Skills count | 6 | 2026-04-14 | Standard skill set |

## Testing

| Tier | When | Command |
|------|------|---------|
| 1 Smoke | After code change | `./install.sh` in empty dir + verify file count |
| 2 Regression | After template change | Compare `example/minimal-project/` with fresh install |
| 3 Integration | Before release | Full P0 checklist in `docs/archive/Release_Checklist.md` |

## Tech Stack

- **Language**: Bash (installer), Python 3.8+ (CLI tools)
- **Runtime**: macOS / Linux / WSL
- **Dependencies**: Python standard library only (no pip packages)

## Information Surfaces

| Surface | Primary Files | What Lives There |
|---------|---------------|------------------|
| Operational | `AI_CONTEXT.md`, `ROADMAP.md`, `VERSION.json`, `.agents/memory.md` | Current state, guardrails, recent decisions |
| Wiki | `docs/knowledge/index.md`, topic pages | Durable background knowledge |
| Execution | `.agents/skills/*.md`, `scripts/*.py` | Repeatable workflows and deterministic maintenance |
| Raw fallback | `docs/raw/*.md` | Detailed source notes (fallback-only) |
| Design docs | `docs/Architecture_Origins.md`, `docs/Design_Principles.md` | Framework lineage and philosophy |

## Concrete Commands

- Smoke test: `./install.sh` in a fresh directory
- CLI status: `python3 scripts/context_hub.py status`
- Search knowledge: `python3 scripts/context_hub.py search <query>`
- Add memory entry: `python3 scripts/context_hub.py memory add "[TYPE] message"`
- Refresh one wiki topic: `python3 scripts/wiki_sync.py refresh <topic>`
- Lint wiki metadata: `python3 scripts/wiki_sync.py lint`
