---
source_id: ingestion-pipeline
title: Ingestion Pipeline Notes
topic_id: Ingestion_Pipeline
related_topics:
  - Annotation_Policy
  - Experiment_Findings
summary: The demo pipeline ingests sanitized experiment notes and produces compact durable wiki pages.
last_updated: 2026-04-13
---

# Ingestion Pipeline Notes

## Context

- The public demo mimics a research repo without exposing private artifacts.
- Every durable topic starts as a markdown source note under `docs/raw/`.

## Durable Notes

- Raw notes are fallback-only and should not be read at startup.
- The compiled wiki is the normal retrieval surface for agents.
- Topic refreshes should be deterministic and small.

## Open Questions

- Should the starter eventually auto-suggest a refresh when a source note changes?
