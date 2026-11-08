# ADR 002: Override precedence

Status: Accepted

## Decision
Global values are fallback defaults rather than universal disable controls.
An explicit true override remains enabled when the global value is false.
An explicit false override remains disabled when the global value is true.
Deleting an override restores inheritance from the global value.

## Rationale
Tenant launch schedules must remain independent of changes to shared defaults.
