---
id: Router_Evaluation
title: Router Evaluation
page_type: topic
build_origin: wiki_sync
source_refs:
  - docs/raw/router_evaluation_source.md
last_updated: 2026-04-13
related_topics:
  - Annotation_Policy
  - Experiment_Findings
---
# Router Evaluation

> Generated from `docs/raw/` notes by `python3 scripts/wiki_sync.py refresh Router_Evaluation`. Edit raw sources first, then rebuild.

## Summary
- **Router Evaluation Notes**: The branch compares baseline, wiki-heavy, and hybrid-router modes on the same prompt suite.

## Compiled Source Notes

### Router Evaluation Notes
- Source ref: `docs/raw/router_evaluation_source.md`
- Source ID: `router-evaluation`
- Last updated: 2026-04-13
- Related topics: `Annotation_Policy`, `Experiment_Findings`

## Context

- Mode A: operational docs + memory + skills
- Mode B: raw sources + compiled wiki + minimal recent-memory use
- Mode C: hybrid-router with explicit lane routing

## Durable Notes

- The hybrid router is expected to win when tasks mix current-state reasoning and durable knowledge.
- A pure wiki-heavy mode risks overusing raw notes or stale operational docs.
- Merge only if the hybrid mode preserves a simple onboarding path.

## Open Questions

- Can lane selection be measured consistently across agents?

## Related Topics
- `Annotation_Policy`
- `Experiment_Findings`

## AI Annotations

<!-- Auto-appended by agents via: python3 scripts/context_hub.py annotate Router_Evaluation "note" -->