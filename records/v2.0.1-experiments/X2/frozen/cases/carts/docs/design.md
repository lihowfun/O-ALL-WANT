# Cart price recalculation

## Context
The trusted worker validates coupon eligibility before calling pricing.
Checkout will call recalculation directly when address or coupon changes.
Carts, prices, coupons and tax schedules share one PostgreSQL database.
Each destination has one rate for all merchandise in this release.

## Goals and requirements
G1. Reprice up to 40 lines with p95 below 150 ms at 100 requests/s.
G2. Store USD amounts as integer cents and retain quotes for checkout.
G3. Discounts reduce merchandise before tax; shipping is excluded from tax.
G4. Round tax half up separately for each discounted line, then sum it.
G5. Reject expired coupons and unmet minimum spends with HTTP 422.
G6. Accept zero or one coupon per cart; stacking is outside this release.
G7. Successful responses contain committed quotes usable immediately.

## Existing behavior
`src/pricing.py` provides coupon discount and tax arithmetic.
The worker passes discounted line amounts to `internal_quote`.
`discount_cents` rejects expired coupons and unmet minimum spends.
`tax_cents` rounds a tax amount expressed in cents.

## Proposed design
Add `POST /v1/carts/{id}/recalculate` with `expected_revision` and `coupon_codes`.
Authenticate the caller and verify cart ownership before reading its contents.
Start a repeatable-read transaction and lock the cart row.
Read lines, address, current prices and destination rate in that transaction.
Return 409 if `expected_revision` differs from the cart revision.
Resolve the requested code through `CouponRepository.get` in this transaction.
This lookup returns the stored coupon even when its expiry is in the past.
Reuse `discount_cents` for eligibility and amount; translate ValueError to 422.
An empty list gives zero discount; more than one code returns 422.
Allocate the discount in proportion to each line's extended price.
Floor shares, then give remaining cents to lines in ascending line-ID order.
Sum the discounted line amounts into taxable merchandise.
Call `tax_cents` once with that sum and the destination rate.
Store line discount allocations and the resulting single tax amount.
Total is discounted merchandise plus tax plus shipping.
Replace the cart's quote and increment a separate quote revision.
Commit before returning; all quote writers acquire the same cart lock.
Errors roll back the transaction and leave the preceding quote intact.

## Data model and interfaces
Cart: id, owner_id, revision, address_id, shipping_cents, quote_revision.
Line: id, cart_id, sku, quantity, unit_price_cents; quantity is positive.
Coupon: code, percent (0–100), min_subtotal_cents, expires_at (UTC).
`CouponRepository.get(code) -> Coupon | None`; missing codes return 422.
`TaxSchedule.get(address_id) -> Decimal` returns a fraction, e.g. 0.10.
Quote: cart_revision, quote_revision, subtotal, discount, tax, shipping, total.
Quote also stores line discount allocations and the selected coupon code.
The v1 response renders all five money fields as two-place USD decimal strings.
Example: `"total": "12.34"`; currency remains `"USD"`.
Retain existing field names and return HTTP 200.
Error responses carry a stable code and no partial quote.

## Worked example
Two $5.00 lines total 1,000 cents; a 10% coupon removes 100 cents.
Its 1,000-cent minimum is met although discounted merchandise is 900 cents.
At 10% tax and 200-cent shipping, tax is 90 cents and total is 1,190 cents.
Shipping contributes no taxable cents under ADR-002.

## Implementation and rollout
1. Add quote storage and repositories; verify allocation sums and rollback.
2. Add the route and ownership checks; test revision conflicts in PostgreSQL.
3. Connect checkout and render supplied strings; test address and coupon changes.
4. Require existing tests, the example and G1 load targets with 40-line carts.
Gate by merchant at 5%, 25%, then 100%, with 24 hours per stage.
Advance with less than 0.5% errors and G1 latency; track errors and lock waits.
On regression disable the route and return checkout to the trusted worker.
Integer quote columns remain readable by the worker during rollback.
Retain additive fields so rollback needs no schema reversal.
