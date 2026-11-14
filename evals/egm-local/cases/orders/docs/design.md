# Reservation redesign

## Goals
Move reservation traffic from one region to three regions without losing stock correctness. The p99 API target is 120 ms at 2,000 reserve requests/s, measured end to end in the load test.

## Data
A reservation is a successful allocation for one order. Each request gets a newly generated reservation UUID.
The rollout uses MongoDB. This plan claims MongoDB is permitted by ADR-001 and schedules cutover without a storage exception or replacement ADR.

## Flow
1. Read the available quantity.
2. If it is sufficient, create a reservation with the new UUID.
3. Update the available quantity with the previously read quantity minus the request quantity.
These are separate writes without a transaction or conditional update, to minimize lock contention. A retried HTTP request repeats all steps.

## Support and retention
The only reservation ledger is deleted after 7 days. Support must answer reservation disputes for the last 30 days using this ledger. No archive is planned.

## Implementation and verification
Implement the new ledger and route traffic to it. Confirm p99 under the stated load. Add a test where two requests concurrently reserve the last unit and a test replaying the same order. The concurrency and retry tests are planned, not already implemented.
