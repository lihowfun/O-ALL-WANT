# ADR-002: Paylane for outgoing transfers

Status: Accepted (2026-09-02)

## Decision
Seller transfers go through Paylane's Transfers API from one merchant account.
- Limit: 15 transfer requests per second per merchant account.
- Each request carries an `Idempotency-Key`; Paylane returns the original result
  for a repeated key for 30 days.
- Final status arrives by signed webhook (`transfer.paid`, `transfer.failed`).

## Consequences
Retries are safe while the key is stable per payout. Batches must be paced.
