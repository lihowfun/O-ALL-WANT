# ADR-001: Append-only points ledger

Status: Accepted
Date: 2026-03-02

## Context
Points are money-like: finance reconciles the points liability monthly.

## Decision
- Every change to a balance is a row in `ledger_entries`. Rows are never
  updated or deleted; corrections are new entries.
- A member's balance is the sum of their entries. Any stored balance is a
  cache and must be written in the same transaction as the entry.

## Consequences
Full audit trail. Balance read cost grows with entry count unless cached.
