---
id: Ingestion_Pipeline
title: Ingestion Pipeline
page_type: topic
build_origin: wiki_sync
source_refs:
  - docs/raw/ingestion_pipeline_source.md
last_updated: 2026-04-13
related_topics:
  - Annotation_Policy
  - Experiment_Findings
---
# Ingestion Pipeline

> Generated from `docs/raw/` notes by `python3 scripts/wiki_sync.py refresh Ingestion_Pipeline`. Edit raw sources first, then rebuild.

## Summary
- **Ingestion Pipeline Notes**: The demo pipeline ingests sanitized experiment notes and produces compact durable wiki pages.

## Compiled Source Notes

### Ingestion Pipeline Notes
- Source ref: `docs/raw/ingestion_pipeline_source.md`
- Source ID: `ingestion-pipeline`
- Last updated: 2026-04-13
- Related topics: `Annotation_Policy`, `Experiment_Findings`

## Context

- The public demo mimics a research repo without exposing private artifacts.
- Every durable topic starts as a markdown source note under `docs/raw/`.

## Durable Notes

- Raw notes are fallback-only and should not be read at startup.
- The compiled wiki is the normal retrieval surface for agents.
- Topic refreshes should be deterministic and small.

## Open Questions

- Should the starter eventually auto-suggest a refresh when a source note changes?

## Related Topics
- `Annotation_Policy`
- `Experiment_Findings`

## AI Annotations

<!-- Auto-appended by agents via: python3 scripts/context_hub.py annotate Ingestion_Pipeline "note" -->
