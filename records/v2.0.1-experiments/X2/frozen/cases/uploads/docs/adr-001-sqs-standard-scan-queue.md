# ADR-001: SQS standard queue for scan jobs

Status: Accepted (2026-08-14)

## Context

Scan jobs must survive worker crashes and deploys without manual replay.

## Decision

Use an SQS standard queue for `scan-jobs`. Delivery is at-least-once and
unordered: a message can be delivered more than once, including after a
worker has already processed it. Every consumer step must be safe to repeat.

## Consequences

No FIFO throughput ceiling; handlers must be idempotent.
