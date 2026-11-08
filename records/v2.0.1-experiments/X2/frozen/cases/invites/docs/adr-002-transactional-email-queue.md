# ADR-002: Transactional email via the shared mail queue

Status: Accepted (2026-05-18)

## Context
Services called the email provider directly and were throttled
during spikes, dropping mail.

## Decision
All transactional email is enqueued on the shared `mail-out` queue.
One sender worker drains it at our provider account limit of
10 messages per second, shared by all services.

## Consequences
Services must not call the provider directly. Enqueue returns a
message id; delivery time depends on queue depth.
