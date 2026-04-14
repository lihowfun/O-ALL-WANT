---
source_id: annotation-policy
title: Annotation Policy Notes
topic_id: Annotation_Policy
related_topics:
  - Ingestion_Pipeline
  - Experiment_Findings
summary: Rolling memory, raw notes, and compiled wiki pages serve different jobs and should not collapse into one file.
last_updated: 2026-04-13
---

# Annotation Policy Notes

## Context

- Teams need a simple rule for where new information should go.

## Durable Notes

- Use `.agents/memory.md` for recent decisions and user corrections.
- Use `docs/raw/` for detailed source material and draft notes.
- Use `docs/knowledge/` for compact durable summaries that future agents can retrieve quickly.

## Open Questions

- Should some annotation categories auto-promote from memory into wiki refresh suggestions?
