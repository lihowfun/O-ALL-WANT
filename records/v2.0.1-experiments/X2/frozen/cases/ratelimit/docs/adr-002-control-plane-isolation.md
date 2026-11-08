# ADR-002: Control-plane isolation

Status: Accepted

## Decision
Gateway request handlers must not query control-plane PostgreSQL, including replicas.
Deliver account quota policies as in-memory snapshots refreshed at most 30 seconds apart.

## Rationale
Control-plane maintenance must not stop public request admission.
Background configuration publishers may access the control-plane database.
