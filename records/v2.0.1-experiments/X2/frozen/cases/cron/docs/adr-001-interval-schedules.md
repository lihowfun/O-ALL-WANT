# ADR-001: Elapsed interval schedules
Status: Accepted

## Decision
The first release supports fixed elapsed-second intervals.
Store due instants as UTC timestamps.
Do not store a timezone or apply daylight-saving adjustments.
Calendar scheduling needs a separate API and decision.

## Consequences
An 86,400-second interval can move relative to local midnight.
Describe these as intervals, never local daily alarms.
