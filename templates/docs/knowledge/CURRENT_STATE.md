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
last_updated: YYYY-MM-DD
related_topics:
  - Experiment_Findings
  - Performance_Baselines
  - Architecture_Decisions
  - Known_Limitations
---

# Current State — Single Compiled Entry Point

> **Purpose**: Any fresh agent session should be able to orient itself by
> reading **only this file**. It is a compiled snapshot of the project's
> current state, distilled from `AI_CONTEXT.md`, `ROADMAP.md`,
> `.agents/memory.md`, and the knowledge topic pages.
>
> **Maintained by AI** (not user). Update this page whenever:
> - a phase status changes
> - a major experiment concludes
> - an architectural decision is made
> - `wiki_sync.py update-state` is invoked

---

## 1. Project Mission (one paragraph)

${PROJECT_MISSION — why does this project exist, what is it trying to achieve?}

## 2. Architecture at a Glance

- **Core components**: ${component list with one-line purpose each}
- **Data flow**: ${where data starts, how it flows, where it ends}
- **Key tech stack**: ${languages, frameworks, infra}

## 3. Current Phase / Milestone

| Phase | Status | Target | Notes |
|-------|:------:|--------|-------|
| ${Phase A} | ✅ done | — | ${1-line summary} |
| ${Phase B} | 🔄 in progress | ${YYYY-MM-DD} | ${blockers if any} |
| ${Phase C} | ⏳ queued | — | ${prerequisite} |

## 4. Recent Decisions (last 5)

> Chronological order — newest first. Copy from `.agents/memory.md`.

1. **[YYYY-MM-DD]** `[DECISION]` ${one-line decision + reason}
2. **[YYYY-MM-DD]** `[EXPERIMENT]` ${name → accepted / rejected}
3. **[YYYY-MM-DD]** `[ARCHITECTURE]` ${change}
4. **[YYYY-MM-DD]** `[BUG]` ${fix summary}
5. **[YYYY-MM-DD]** `[INSIGHT]` ${discovery}

## 5. Active Experiments

> Only list experiments that are running or awaiting analysis.

| ID | Name | Status | Next Step |
|----|------|:------:|-----------|
| ${id} | ${name} | running | ${what to check} |

## 6. Known Blockers / Risks

- ${blocker 1 — who owns it, what's the unblock path}
- ${risk 1 — likelihood × impact, mitigation}

## 7. What Comes Next (P0 / P1 / P2)

- **P0**: ${must-do, gating next phase}
- **P1**: ${important, schedulable}
- **P2**: ${nice-to-have}

## 8. Pointers for Deeper Reading

| Need | File |
|------|------|
| Architecture details | `AI_CONTEXT.md` |
| Roadmap / phase plan | `ROADMAP.md` |
| Recent event log | `.agents/memory.md` |
| Wiki map | `docs/knowledge/index.md` |
| Experiments archive | `docs/knowledge/EXPERIMENT_LOG.md` |
| Baselines | `docs/knowledge/Performance_Baselines.md` |
| Known issues | `docs/knowledge/Known_Limitations.md` |

## 9. Common Commands (copy-paste ready)

> Keep these up to date so any fresh agent can execute without trial and error.

```bash
# Python env (customize per project)
PY=${PYTHON_BIN:-python3}

# Wiki maintenance
$PY scripts/wiki_sync.py lint
$PY scripts/wiki_sync.py build
$PY scripts/wiki_sync.py refresh <Topic>

# Non-interactive state / experiment updates (AI auto-invoked)
$PY scripts/wiki_sync.py add-experiment \
  --name "${exp_name}" --status "accepted|rejected|running" \
  --result "${one-line metric}" --conclusion "${decision}"

$PY scripts/wiki_sync.py update-state \
  --phase "${phase_id}" --status "${done|in_progress|queued}" \
  --note "${one-line update}"

# Context hub
$PY scripts/context_hub.py status
$PY scripts/context_hub.py annotate <Topic> "${note}"
```

---

## AI Annotations

<!-- Auto-appended by agents via `python3 scripts/wiki_sync.py update-state` -->
