---
source_id: router-evaluation
title: Router Evaluation Notes
topic_id: Router_Evaluation
related_topics:
  - Experiment_Findings
  - Annotation_Policy
summary: The branch compares baseline, wiki-heavy, and hybrid-router modes on the same prompt suite.
last_updated: 2026-04-13
---

# Router Evaluation Notes

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
