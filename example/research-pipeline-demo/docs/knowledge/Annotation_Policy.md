---
id: Annotation_Policy
title: Annotation Policy
page_type: topic
build_origin: wiki_sync
source_refs:
  - docs/raw/annotation_policy_source.md
last_updated: 2026-04-13
related_topics:
  - Experiment_Findings
  - Ingestion_Pipeline
---
# Annotation Policy

> Generated from `docs/raw/` notes by `python3 scripts/wiki_sync.py refresh Annotation_Policy`. Edit raw sources first, then rebuild.

## Summary
- **Annotation Policy Notes**: Rolling memory, raw notes, and compiled wiki pages serve different jobs and should not collapse into one file.

## Compiled Source Notes

### Annotation Policy Notes
- Source ref: `docs/raw/annotation_policy_source.md`
- Source ID: `annotation-policy`
- Last updated: 2026-04-13
- Related topics: `Experiment_Findings`, `Ingestion_Pipeline`

## Context

- Teams need a simple rule for where new information should go.

## Durable Notes

- Use `.agents/memory.md` for recent decisions and user corrections.
- Use `docs/raw/` for detailed source material and draft notes.
- Use `docs/knowledge/` for compact durable summaries that future agents can retrieve quickly.

## Open Questions

- Should some annotation categories auto-promote from memory into wiki refresh suggestions?

## Related Topics
- `Experiment_Findings`
- `Ingestion_Pipeline`

## AI Annotations

<!-- Auto-appended by agents via: python3 scripts/context_hub.py annotate Annotation_Policy "note" -->
