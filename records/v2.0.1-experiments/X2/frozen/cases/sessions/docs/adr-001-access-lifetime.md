# ADR-001: Access lifetime
Status: Superseded by ADR-002 (docs/adr-002-mobile-policy.md).
## Context
The first release lacked online revocation checks.
## Decision
Access tokens last 300 seconds.
Refresh sessions expire 30 days after login.
## Consequences
Clients refresh before access expiry.
