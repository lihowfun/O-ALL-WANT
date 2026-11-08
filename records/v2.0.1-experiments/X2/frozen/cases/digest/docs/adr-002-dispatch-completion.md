# ADR-002: Dispatch completion

Status: Accepted

## Decision
The service promises provider acceptance, not delivery to an inbox.
A successful put_message acceptance completes dispatch.
Mailbox bounces do not reopen digest jobs.
Provider idempotency keys are retained for 30 days.

## Rationale
Mailbox delivery cannot be made transactional with our job database.
