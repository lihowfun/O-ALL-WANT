# ADR-002: Contact details in the support search index

Status: Accepted

## Context
Agents locate customers by email or phone; redacting them defeats the index.

## Decision
The support search index may store `email` and `phone` in clear text. Its
cluster is reachable only from the support console VPC, and the console
requires the `support_agent` role. No other consumer may read the index.

Data erased under a deletion request must leave every index within 24 h.
