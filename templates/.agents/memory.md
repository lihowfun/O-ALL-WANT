# Agent Memory — Decision & Finding Log

> **Format**: `## [YYYY-MM-DD] [TAG] Title`, then write a conclusion. Newest entries on top.
>
> **Available TAGs**:
> - Kind: `[BUG]` `[INSIGHT]` `[DECISION]` `[WORKAROUND]` `[EXPERIMENT]` `[ARCHITECTURE]` `[REVIEW]` `[FIX]` `[FEATURE]`
> - Evidence tier (optional, see `.agents/skills/classify-evidence.md`):
>   `[T1]` WIP · `[T2]` Observation · `[T3]` Confirmed · `[T4]` Baseline · `[T5]` Frozen
> - Qualifier: `[CAVEAT: ...]` — e.g. `[CAVEAT: single seed]`, `[CAVEAT: one source]`, `[CAVEAT: one environment]`
>
> **How to write**:
> - Edit this file directly, or
> - `python3 scripts/context_hub.py memory add "[TAG] Title - Details"`

---

## [2026-01-15] [DECISION] Initialized agent memory system

Adopted hybrid router architecture:
- Lane 1: Operational docs (`AI_CONTEXT.md`, `ROADMAP.md`, `VERSION.json`, recent memory)
- Lane 2: Compiled wiki (`docs/knowledge/`) — durable topic-indexed knowledge
- Lane 3: Execution skills (`.agents/skills/`) — reusable workflows
- `docs/raw/` remains fallback-only source material for rebuilding the wiki

All sessions must end with a 4-section report. All failures must be logged.
See `.agents/skills/self-improving.md` for enforcement rules.

---

<!-- New entries go above this line. Keep newest on top. -->
<!-- Archive entries older than 30-50 items to docs/knowledge/ -->
