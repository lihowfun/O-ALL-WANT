# ADR-012: lookup cache exception
Status: accepted; revision r1; date 2026-10-20.
For the customer lookup service only, Redis is an approved disposable cache backed by PostgreSQL. It may contain public customer display names, never authentication tokens. Cache loss must fall back to PostgreSQL. This supersedes ADR-002 only for this service.
