# Agent Memory — Decision & Finding Log

> **Format**: `## [YYYY-MM-DD] [TAG] Title`, then write a conclusion. Newest entries on top.
>
> **Available TAGs**: `[BUG]` `[INSIGHT]` `[DECISION]` `[WORKAROUND]` `[EXPERIMENT]` `[ARCHITECTURE]`
>
> **How to write**:
> - Edit this file directly, or
> - `python scripts/context_hub.py memory add "[TAG] Title - Details"`

---

## [2026-01-15] [DECISION] Initialized agent memory system

Adopted three-layer memory architecture:
- Layer 1: Built-in session memory (agent-native)
- Layer 2: Rolling memory (this file) — cross-session decisions
- Layer 3: Knowledge base (`docs/knowledge/`) — permanent topic-indexed knowledge

All sessions must end with a 4-section report. All failures must be logged.
See `.agents/skills/self-improving.md` for enforcement rules.

---

<!-- New entries go above this line. Keep newest on top. -->
<!-- Archive entries older than 30-50 items to docs/knowledge/ -->
