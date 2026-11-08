# ADR-002: Invoice numbering and immutability

Status: Accepted (2024-06-02)

## Context

Invoices are tax documents. Each is reported to the tax authority when it is
finalized, and a copy is sent to the customer.

## Decision

- Invoice numbers are sequential per calendar year (`INV-2026-0000001`) and
  assigned at finalization, so drafts never consume a number.
- A finalized invoice is never modified. Any correction, including added
  charges, is issued as a new invoice or a credit note referencing the
  original number.
