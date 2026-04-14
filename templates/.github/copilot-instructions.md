# Agent Memory Framework — Copilot Instructions

Read `AI_CONTEXT.md` at repo root for full project context.
Read `CLAUDE.md` (or `AGENTS.md`) for session rules + lazy-read protocol.

## Quick Rules
1. Never read all .md files at startup — use the task-based routing table
2. Never re-run experiments listed in `VERSION.json` `do_not_rerun`
3. If `.agents/skills/` has a matching skill, follow it before going ad-hoc
4. End every task with a 4-section report (What / Verified / Docs updated / Next)
5. Record all failures to `.agents/memory.md`
6. Use `docs/raw/` only when the compiled wiki is missing or stale
