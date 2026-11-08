# ADR-002: Promotion and shipping rules

Status: Accepted

## Decision
Minimum spend uses merchandise subtotal before discounts, excluding shipping.
A qualifying coupon remains eligible when its discount lowers that subtotal.
Shipping is exempt from tax in the supported merchant program.
Merchandise alone forms the taxable base after coupon allocation.

## Rationale
These are the checkout contract for this release.
Stacking is unsupported; reject requests containing multiple coupon codes.
