# ADR-001: Click events on the shared event bus

Status: Accepted (2025-03-14)

## Context
Analytics needs click data without adding writes to the redirect path.

## Decision
Clicks are published to the `clicks` topic on the shared event bus.
Producers use acks=all and retry until acknowledged; a redirect is answered
only after its event is acknowledged. Delivery is at-least-once: an event
may reach a consumer more than once after a producer retry or a consumer
restart. Each event carries a producer-generated `event_id`.

## Consequences
Consumers manage their own offsets.
