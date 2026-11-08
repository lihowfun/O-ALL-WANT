# ADR-001: Receiver contract
Status: Accepted
## Context
Third-party receivers can time out after accepting a request.
## Decision
Attempts may repeat within a six-attempt budget.
Receivers deduplicate using the event id within their endpoint.
Distinct events are independent notifications and may arrive in any order.
Each payload describes a completed occurrence, not a mutable resource snapshot.
## Consequences
Parallel dispatch is supported; FIFO delivery is not part of the contract.
