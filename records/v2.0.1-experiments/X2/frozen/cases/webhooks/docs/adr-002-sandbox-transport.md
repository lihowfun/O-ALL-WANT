# ADR-002: Sandbox transport
Status: Accepted
## Context
Sandbox tenants use local development receivers reached through a test gateway.
## Decision
Production registrations accept only HTTPS URLs.
Sandbox registrations may use HTTP URLs through the isolated sandbox gateway.
Sandbox carries synthetic events only; production events cannot enter its queue.
Both environments apply destination validation and sign all requests.
## Consequences
The dispatcher uses the endpoint's registered environment and gateway.
