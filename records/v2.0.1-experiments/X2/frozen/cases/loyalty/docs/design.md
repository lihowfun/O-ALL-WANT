# Design: Real-time Earn and Points Redemption

Status: In review
Authors: Loyalty team

## Context

Members earn points today through a nightly batch that calls
`earn_for_order` in `src/ledger.py`. Members cannot spend points yet. This
design moves earning to real time and adds redemption at checkout.

Order events come from the commerce event bus (topic `orders.v2`). The bus
delivers at least once. After incidents the bus team replays a topic from
any offset within the last 7 days.

## Goals and requirements

- R1: Points are credited within 2 minutes of `order.paid` (p99).
- R2: A paid order earns points exactly once, including across replays.
- R3: A redemption never takes a member's balance below zero.
- R4: Redemption API p99 latency under 150 ms at peak.
- R5: Members can view and redeem only their own points.
- R6: Promotion peak of 36,000 order events/min and 9,000 redemptions/min.

Non-goals: points expiry, tiers, partner points.

## Proposed design

### Earn consumer

A new `earn-consumer` service subscribes to `orders.v2` and handles
`order.paid` and `order.refunded`:

- `order.paid`: call `earn_for_order` (1 point per whole currency unit).
- `order.refunded`: append a `clawback` entry for the points the order
  earned. Clawbacks are applied in full even if the balance goes negative.
  If the order redeemed points, a `redeem_reversal` entry returns them
  (`source_ref = reversal:<order_id>`), unless one already exists.

Each event is written in one transaction that first takes the member's
advisory lock (as in redemption, below).

Before handling an event the consumer checks Redis for `evt:<event_id>`; if
present it acks and skips. After the ledger write commits it sets the key
with a 24-hour TTL, then acks. Failed writes are retried with backoff.

The consumer runs 4 workers in one consumer group. Load tests of the
per-event transaction, writing two entries per event, sustain 160
events/s per worker, giving 640 events/s.

### Redemption

Checkout calls `POST /v1/redemptions` with body
`{member_id, order_id, points}`. The API gateway validates the member's
session JWT (signature and expiry) and forwards the request; the ledger
service accepts gateway-authenticated requests as is.

Requests with `points` that is not a positive integer get 400. Otherwise
the ledger service handles a redemption in one transaction:

1. `pg_advisory_xact_lock` on a hash of `member_id`.
2. If an entry with `source_ref = redeem:<order_id>` exists, return it.
3. Read the balance from `member_balances`.
4. If the balance is below `points`, return 409.
5. Call `append_entry` with a `redeem` entry of `-points`.

If the order is not placed, checkout calls
`POST /v1/redemptions/{order_id}/cancel`, which takes the same lock and
appends that `redeem_reversal` entry, unless one already exists.

`member_balances` keeps step 3 a single-row read. The table already exists:
`append_entry` upserts it in the same transaction as each entry insert, as
ADR-001 requires.

Redemptions run on 6 API pods, each sized for 25 requests/s.

## Data model and interfaces

Table `ledger_entries(id, member_id, delta, kind, source_ref, created_at)`,
kinds `earn`, `redeem`, `redeem_reversal`, `clawback`. New index
`ix_ledger_source_ref` on `source_ref`. No other schema changes.

Events consumed:

- `order.paid {event_id, order_id, member_id, amount_cents, occurred_at}`
- `order.refunded {event_id, order_id, member_id, occurred_at}`

API:

- `POST /v1/redemptions` -> `200 {entry_id, balance}` or
  `409 {error: "insufficient_points", balance}`
- `POST /v1/redemptions/{order_id}/cancel` -> `200 {balance}`
- `GET /v1/members/{member_id}/balance` -> `200 {balance}`

## Rollout

1. Run `earn-consumer` in shadow mode for one week, logging entries
   without writing them; compare with the nightly batch daily.
2. Enable writes for 5% of members by member-id hash, switching at a
   nightly batch cutoff T: the batch handles the cohort's events with
   `occurred_at` before T, the consumer those at or after T.
3. Ramp to 100% the same way over two weeks; then delete the batch job.
4. Ship redemption behind the `redeem_enabled` flag: staff accounts first,
   then all members after one week without incidents.

Rollback: turn off `redeem_enabled`; pause `earn-consumer`. Unacked events
stay on the bus and are processed on resume.

Done when R1-R6 hold over 7 days in production and ledger totals match
finance's monthly reconciliation.
