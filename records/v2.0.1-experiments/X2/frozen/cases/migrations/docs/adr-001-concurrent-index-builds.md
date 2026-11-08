# ADR-001: Concurrent index builds run outside a transaction
Status: Accepted (2026-03-02)

## Context
CREATE INDEX CONCURRENTLY cannot run inside a transaction block. A plain CREATE INDEX
blocks writes on large tables for minutes.

## Decision
A migration file starting with `-- runner: no-transaction` runs outside a transaction.
Such a file holds exactly one CREATE INDEX CONCURRENTLY IF NOT EXISTS statement. Before
running it, the runner drops an INVALID index of the same name left by a failed attempt.

## Consequences
A failed build can be re-run without manual cleanup.
