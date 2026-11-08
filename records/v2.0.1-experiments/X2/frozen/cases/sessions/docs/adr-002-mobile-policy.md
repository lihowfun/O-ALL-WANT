# ADR-002: Mobile authentication
Status: Accepted. Supersedes ADR-001.
## Context
Native apps cannot protect embedded shared secrets.
## Decision
Use public clients, system-browser code flow and PKCE S256.
Access tokens last at most 600 seconds, capped by session expiry.
Rotation preserves the original 30-day absolute deadline.
## Consequences
All resource gateways check authoritative revocation on every call.
