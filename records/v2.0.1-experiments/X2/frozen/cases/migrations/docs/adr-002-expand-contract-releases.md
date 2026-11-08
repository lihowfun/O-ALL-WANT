# ADR-002: Expand and contract ship in separate releases
Status: Accepted (2026-05-18)

## Context
Every deploy must be reversible by redeploying the previous application release with
no schema change. That release still reads and writes the old columns.

## Decision
Destructive DDL (DROP COLUMN, DROP TABLE, type narrowing) appears only in contract
migrations. A contract ships in a later release than the code that stopped using the
affected objects, and runs only after that release has been in production for 7 days.

## Consequences
Old columns remain for at least one release cycle; the storage cost is accepted.
