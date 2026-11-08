# ADR-001: v1 money encoding

Status: Accepted

## Decision
All `/v1` pricing responses encode money as integer USD cents.
Checkout's quote decoder rejects strings; additions to v1 retain this encoding.
Decimal strings require a `/v2` endpoint and a coordinated client release.

## Scope
This applies to recalculation and initial quotes.
