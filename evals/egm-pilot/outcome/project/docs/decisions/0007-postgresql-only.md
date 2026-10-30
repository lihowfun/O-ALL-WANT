# 0007. PostgreSQL is the only datastore for service state

- Status: accepted
- Date: 2026-03-14
- Revision: r2

## Context

In November 2025 the delivery log ran on a separate MongoDB cluster. A failed
replica election lost two hours of delivery records, and the cluster needed
skills nobody on the team kept current. The team retired that cluster and moved
the delivery log back into PostgreSQL.

## Decision

All persistent state of the services in this repository, including queues and
delivery records, lives in the shared PostgreSQL 16 cluster. A design that
proposes any other datastore needs an architecture review before it is drafted.

## Consequences

- One backup, failover and access-control setup for every service.
- Cross-region reads use PostgreSQL logical replication.
