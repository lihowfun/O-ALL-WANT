# ADR-001: Money as integer minor units

Status: Accepted (2024-03-11)

## Decision

All monetary amounts are stored and computed as integer minor units (cents).
Where a fraction arises (proration, percentage discounts) the result is
rounded once, half-even, to whole cents. Floats are never used for money.

Invoice totals under 50 cents, the card processor's minimum charge, are not
charged and not written off; they are carried as a balance line onto the
subscription's next invoice.
