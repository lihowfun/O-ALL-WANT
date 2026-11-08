# ADR-001: Account quota contract

Status: Accepted

## Decision
Use UTC-aligned one-second buckets for account allowances.
An account can consume its full allowance on each side of a bucket boundary.
/healthz is exempt from authentication and account quotas.
It returns fixed local status and cannot dispatch to application upstreams.

## Consequences
Clients that need evenly spaced requests implement their own pacing.
All other public routes require authentication and account quota enforcement.
