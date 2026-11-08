# ADR-001: Publish database changes through a change_log relay

Status: Accepted

## Decision
Row triggers append to `change_log`. `src/change_publisher.py` relays rows
to Kafka topics `cdc.<table>`, keyed by primary key, so per-key order is kept.

Delivery is at-least-once: the relay saves its cursor only after the
producer flush, so a restart can republish a batch. Consumers must
tolerate duplicate events.

## Consequences
Consumers never query the primary database to learn about changes.
