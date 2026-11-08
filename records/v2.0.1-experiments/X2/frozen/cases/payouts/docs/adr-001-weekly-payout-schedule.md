# ADR-001: Weekly payout schedule and minimum payout

Status: Accepted (2026-08-18)

## Context
Each bank transfer costs a flat $0.25, and finance wants one fixed payout day.

## Decision
- Sellers are paid weekly; the run starts Monday 02:00 UTC.
- A seller is eligible when their settled balance is at least $25.00.
- Smaller balances carry forward to the next weekly run and are never forfeited.

## Consequences
Small sellers may wait several weeks; the dashboard shows the carried balance.
