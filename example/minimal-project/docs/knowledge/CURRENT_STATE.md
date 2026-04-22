---
id: CURRENT_STATE
title: Current State — Single Compiled Entry Point
page_type: topic
build_origin: manual
source_refs:
  - AI_CONTEXT.md
  - ROADMAP.md
  - .agents/memory.md
  - docs/knowledge/index.md
last_updated: 2026-01-01
related_topics:
  - Experiment_Findings
  - Performance_Baselines
  - Architecture_Decisions
  - Known_Limitations
---

# Current State — Single Compiled Entry Point

> **Purpose**: Any fresh agent session should be able to orient itself by
> reading **this file alone**. It is a compiled snapshot of the project's
> current state, distilled from `AI_CONTEXT.md`, `ROADMAP.md`,
> `.agents/memory.md`, and the knowledge topic pages.
>
> **This template is optional.** Keep it if your project has enough moving
> parts that a single compiled entry-point saves repeated re-reading. Delete
> it if your `AI_CONTEXT.md` already serves as the startup orientation.
>
> **Maintained by AI** (not user). An agent should update this page
> whenever:
>
> - a phase status changes
> - a major experiment concludes
> - an architectural decision is made
> - a recurring question ("what phase are we in?") required reading 3+ files
>   to answer — that means this page is stale

---

## 1. Project Mission (one paragraph)

*One paragraph. Example: "We're building a biomedical GNN that predicts
drug-target interactions from a heterogeneous knowledge graph. Goal: match
or exceed published SOTA on DTI-Bench while keeping training under 24h on
a single A100."*

Replace with your project's actual mission, then delete the example text.

## 2. Architecture at a Glance

- **Core components**: *two-to-four lines, one component per line*
- **Data flow**: *one sentence — where data starts, how it flows, where it ends*
- **Key tech stack**: *languages, frameworks, infra*

## 3. Current Phase / Milestone

| Phase | Status | Target | Notes |
|-------|:------:|--------|-------|
| Phase name | ✅ done | — | one-line summary |
| Current phase | 🔄 in progress | 2026-XX-YY | what unblocks the next step |
| Next phase | ⏳ queued | — | prerequisite |

## 4. Recent Decisions (last 5)

> Chronological — newest first. Copy from `.agents/memory.md` when syncing.

1. **[2026-01-01]** `[DECISION]` one-line decision + reason
2. **[2026-01-01]** `[EXPERIMENT]` experiment name → accepted / rejected
3. **[2026-01-01]** `[ARCHITECTURE]` change
4. **[2026-01-01]** `[BUG]` fix summary
5. **[2026-01-01]** `[INSIGHT]` discovery

## 5. Active Experiments

> Only list experiments that are running or awaiting analysis. Drop this
> section entirely if your project does not run experiments.

| ID | Name | Status | Next Step |
|----|------|:------:|-----------|
| — | — | — | — |

## 6. Known Blockers / Risks

- *blocker — owner, unblock path*
- *risk — likelihood × impact, mitigation*

## 7. What Comes Next (P0 / P1 / P2)

- **P0**: must-do, gating next phase
- **P1**: important, schedulable
- **P2**: nice-to-have

## 8. Pointers for Deeper Reading

| Need | File |
|------|------|
| Architecture details | `AI_CONTEXT.md` |
| Roadmap / phase plan | `ROADMAP.md` |
| Recent event log | `.agents/memory.md` |
| Wiki map | `docs/knowledge/index.md` |
| Baselines | `docs/knowledge/Performance_Baselines.md` |
| Known issues | `docs/knowledge/Known_Limitations.md` |

## 9. Common Commands (copy-paste ready)

> Keep these current so any fresh agent can execute without trial and error.

```bash
PY=python3

# Wiki maintenance
$PY scripts/wiki_sync.py lint                  # metadata + quality lint
$PY scripts/wiki_sync.py lint --strict         # also flags unfilled placeholders + skill issues
$PY scripts/wiki_sync.py stale --threshold 30  # report pages untouched > N days
$PY scripts/wiki_sync.py refresh <Topic>       # recompile one topic
$PY scripts/wiki_sync.py build                 # recompile every topic

# Context hub
$PY scripts/context_hub.py status              # version + recent decisions + topics
$PY scripts/context_hub.py search "<keyword>"  # find knowledge pages
$PY scripts/context_hub.py memory add "[TAG] content"  # new newest-first memory entry
$PY scripts/context_hub.py annotate <Topic> "<note>"   # append dated annotation

# Harness health
./scripts/harness_check.py                     # full 8-check local gate (same as CI)
```

---

## AI Annotations

<!-- Agents append dated annotations here as the project evolves.
     Example entry:
     - [2026-02-14] Phase B blocked on dataset licensing; owner reached out to vendor. -->
