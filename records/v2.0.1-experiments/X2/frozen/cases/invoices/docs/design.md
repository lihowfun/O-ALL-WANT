# Design: Parallel monthly invoice run

## Context

The monthly run (`src/invoice_runner.py`) invoices active subscriptions one
at a time in one process. At 2.4M active subscriptions it no longer finishes
before customers start their day, and usage that arrives after the run waits
a full month to be billed.

## Goals and requirements

- R1: Invoice all ~2.4M active subscriptions within 6 hours of run start
  (00:30 UTC on the 1st).
- R2: Retrying or resuming a run never charges the same amount twice.
- R3: Usage arriving up to 48 hours after the run is billed in its own period.
- R4: Customers get a PDF of every invoice by email.
- R5: PDFs are retained for 7 years.

Non-goals: changes to pricing, tax rules or the payment provider.

## Proposed design

### Workers

A coordinator splits active subscriptions into shards of 5,000 and enqueues
them on `invoice-shards`. A pool of 12 worker processes consumes shards, each
handling one subscription at a time. Cost per subscription is dominated by the
tax quote call (p50 120 ms); measured end to end it is ~150 ms.

For each subscription a worker:

1. Creates the draft invoice, or resumes the existing one for
   `(subscription_id, period_start)` from its current status.
2. Builds lines. Plan changes reuse `prorate_cents()` in
   `src/proration.py`, which already rounds half-even on integer cents.
3. Finalizes the invoice (assigns its number) and charges the card with
   idempotency key `invoice:{invoice_id}`.
4. Renders and uploads the PDF and emails the customer a link.

Totals under 50 cents are not charged; they are carried as a balance line
onto the next month's invoice.

### Late usage

Usage for a closed period that arrives within 48 hours of the run is applied
to the finalized invoice: the worker appends the usage lines, recomputes the
total, charges the difference with key `invoice:{invoice_id}:adj:{n}`,
re-renders the PDF and re-sends the email. Later usage rolls into the next
period as today.

### PDF delivery

PDFs are uploaded to bucket `billing-invoice-pdfs` at
`invoices/{invoice_number}.pdf` with a public-read ACL, and the email links to
`https://files.lumen.example/invoices/{invoice_number}.pdf` so customers can
open them without signing in. A PDF shows billing name and address, line
items, and card brand and last four digits.

Storage: ~80 KB x 2.4M per month x 84 months = ~16 TB at full retention.

## Data model

```
invoices(
  invoice_id      uuid primary key,
  subscription_id uuid not null,
  period_start    date not null,
  number          text unique,     -- set at finalization
  status          text not null,   -- draft | finalized | paid | failed
  total_cents     bigint not null,
  unique (subscription_id, period_start)
)
invoice_lines(invoice_id uuid, kind text, amount_cents bigint)
```

## Rollout

1. Add the unique index after checking existing rows for duplicates.
2. Ship coordinator and workers behind `invoice_run.parallel`. Run December
   in shadow mode: drafts written to schema `invoice_shadow`, no charges or
   emails; compare totals with the legacy run.
3. January: parallel workers live; legacy runner kept one month as fallback.
4. Enable late-usage adjustments once January is reconciled.
5. Remove the legacy runner.
