---
source_id: experiment-findings
title: Experiment Findings Source Notes
topic_id: Experiment_Findings
related_topics:
  - Router_Evaluation
  - Ingestion_Pipeline
summary: The demo keeps a compact ledger of experiment conclusions so agents do not need to scan full notebooks.
last_updated: 2026-04-13
---

# Experiment Findings Source Notes

## Context

- Research repos often accumulate too many partial experiment notes.
- The public demo keeps only the conclusion layer in the compiled wiki.

## Durable Notes

- Best current recommendation: merge the hybrid router only if it clearly beats or matches the baseline.
- Do not merge the wiki-heavy mode by default unless it wins cleanly.
- The example should remain public-safe and easy to inspect.

## Open Questions

- Should the starter include a prompt-suite template for A/B/C comparisons?
