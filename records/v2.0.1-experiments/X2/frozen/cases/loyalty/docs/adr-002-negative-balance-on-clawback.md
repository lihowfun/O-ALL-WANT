# ADR-002: Clawbacks may make balances negative

Status: Accepted
Date: 2026-05-18

## Context
A member can earn points, redeem them, then refund the original order.
Partial clawbacks would leave the member with points nobody paid for.

## Decision
Refund clawbacks are always applied for the full earned amount, even if the
balance becomes negative. Only redemptions are held to the zero floor.
A negative balance is repaid from future earns.

## Consequences
The app shows negative balances. Finance accepted the exposure.
