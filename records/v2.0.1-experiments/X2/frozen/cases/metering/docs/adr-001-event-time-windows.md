# ADR-001: Bill by event time with a 48-hour close

Status: Accepted

## Context
Clients spool events and may deliver them hours after they occur.
Exported invoice lines must never change.

## Decision
Hourly rollups are keyed by event timestamp, not receipt time. A rollup
closes 48 hours after its hour ends and is immutable from then on.
Events for a closed hour are written to `usage_adjustments`. The
billing service reads unbilled adjustments directly when it builds the
tenant's next invoice, and sets `billed_in`.

## Consequences
Late usage is billed one cycle later instead of reopening an invoice.
