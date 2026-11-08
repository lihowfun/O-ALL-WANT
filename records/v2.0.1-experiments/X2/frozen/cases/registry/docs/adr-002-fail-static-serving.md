# ADR-002: Serving nodes fail static when the registry is unavailable

Status: Accepted

## Context
The registry is a single regional service. The inference fleet has a higher
availability target than the registry.

## Decision
Serving nodes cache the last accepted assignment per model and keep serving it
while the registry is unreachable. They never fall back to a default version.

## Consequences
Assignments, including rollbacks, cannot change during a registry outage. We
accept this: serving continuity outweighs changing versions mid-outage.
