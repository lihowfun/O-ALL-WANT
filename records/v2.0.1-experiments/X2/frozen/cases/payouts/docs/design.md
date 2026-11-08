# Design: Weekly Seller Payouts

## Context

Finance pays sellers by hand: every Friday they export settled ledger balances
and upload a transfer file to the bank portal, about six hours of work a week.
This design automates weekly payouts on top of the existing ledger
(`src/ledger.py`).

## Goals and requirements

- Pay every eligible seller once per week (ADR-001).
- Support 60,000 active sellers now and 90,000 within a year.
- Finish the batch inside its window, Monday 02:00-04:00 UTC.
- Never pay out a ledger entry more than once.
- Sellers see the amount and status of each payout in the dashboard.

Non-goals: instant payouts; currencies other than USD.

## Proposed design

### Computation

The `payout-batch` job starts Monday 02:00 UTC. Per seller it selects ledger
entries with `status = 'settled'` whose order is outside the hold window given
by `HoldPolicy`. `record_refund()` writes refunds as separate rows with
`kind = 'refund'` and negative `amount_cents`, so the payout amount is
`SUM(amount_cents)` over the selected rows.

If the amount is below $25.00 the seller is skipped and the entries stay
`settled` for the next run (ADR-001).

### Transfer

In one transaction per seller the job inserts a `payouts` row (`pending`) and
sets the selected entries to `paid_out` with that `payout_id`. After commit it
calls Paylane with `Idempotency-Key: payout-<payout_id>`, retrying timeouts and
5xx with the same key (ADR-002). Each run, restarts included, first re-sends
every `pending` payout created in the last 21 days with its original key,
inside Paylane's 30-day key window; older `pending` payouts are not re-sent and
are listed for finance to reconcile with Paylane. Paylane webhooks set the
payout to `paid` or `failed`; on `failed` its entries go back to `settled` with
`payout_id` cleared.

Throughput: Paylane allows 15 transfers per second on our account (ADR-002).
90,000 sellers take 6,000 s, i.e. 100 minutes, inside the 2-hour window.

### Seller API

`GET /v1/payouts` lists payouts for the seller in the JWT `sub` claim, newest
first. `GET /v1/payouts/{payout_id}` returns amount, status, period end, last
four digits of the destination account and the included orders. The gateway
verifies the session JWT; the detail handler loads the payout by `payout_id`
and returns it.

## Data model

```sql
CREATE TABLE payouts (
  payout_id    BIGSERIAL PRIMARY KEY,
  seller_id    BIGINT NOT NULL,
  period_end   DATE NOT NULL,
  amount_cents BIGINT NOT NULL,
  status       TEXT NOT NULL,  -- pending | paid | failed
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE ledger_entries ADD COLUMN payout_id BIGINT REFERENCES payouts;
```

## Rollout plan

1. Migration `0012_payouts` adds the table and column. Done when applied in
   staging and production.
2. Build `payout-batch` against the Paylane sandbox. Done when a staging run on
   a copy of last week's ledger matches finance's totals to the cent.
3. Shadow mode for two weeks: compute payouts into a report for finance without
   changing ledger entries or calling Paylane. Done when both weeks match the
   manual run.
4. Cut over: stop the manual export and enable Paylane calls. Rollback: stop
   creating new payouts but keep re-sending `pending` ones with their original
   keys until webhooks mark each `paid` or `failed`, then resume the manual
   export, which picks up the `settled` entries.

## Open questions

None blocking.
