# Agent Memory — Decision & Finding Log

---

## [2026-03-14] [DECISION] PostgreSQL is the only datastore for notify service state

Conclusion: queues and delivery records stay in the shared PostgreSQL 16 cluster.
The separate MongoDB delivery-log cluster was retired after the November 2025
replica-election incident; any other datastore needs an architecture review
before a design proposes it.
Scope: every service in this repository.
Source: docs/decisions/0007-postgresql-only.md (revision r2, accepted 2026-03-14).
Verified: 2026-03-14 against src/notify/store.py and src/notify/config.py
(DELIVERY_DSN is a PostgreSQL DSN).
