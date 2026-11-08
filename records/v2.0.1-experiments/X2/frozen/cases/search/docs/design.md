# Design: Customer search index fed by change events

Status: In review. Owner: Search Platform.

## Context

Support agents find customers with `ILIKE` queries on the primary Postgres
database: 2-9 s on the 90M-row `customers` table. Customer and billing
changes already flow through the change_log relay (ADR-001), so we can keep
an OpenSearch index current from those events instead.

## Goals and requirements

- R1: Search p95 under 300 ms by name, email, phone or customer id.
- R2: Changes searchable within 10 s (p99) of the database commit.
- R3: Sustain the 1,800 events/s peak with at least 25% headroom.
- R4: Each document carries `open_balance_cents`; agents filter on it in
  the console to choose customers for payment-reminder calls.
- R5: Customers erased by a deletion request leave search within 24 h
  (ADR-002).
- R6: A full rebuild fits the 8-hour Sunday maintenance window.

## Proposed design

A new service, `search-indexer`, consumes `cdc.customers` and
`cdc.invoices` and writes to alias `customers` via the bulk API.

`publish_change()` in `src/change_publisher.py` emits one event per
INSERT, UPDATE and DELETE in `change_log`, with `op` = `c`, `u` or `d`
and the row image in `after`. The indexer handles:

- `cdc.customers` `c`/`u`: partial upsert of document `pk` with name,
  email, phone, country and status from `after`.
- `cdc.customers` `d`: delete document `pk`. The account service
  hard-deletes the `customers` row on a deletion request, meeting R5.
- `cdc.invoices` `c`: scripted upsert on document `after.customer_id`:
  `open_balance_cents += after.amount_cents`.
- `cdc.invoices` `u` with `after.status` = `paid`: scripted update
  `open_balance_cents -= after.amount_cents`. Invoice amounts never
  change after creation; only `status` does.

The indexer batches up to 1,000 actions or 2 s, sends one bulk request,
then commits Kafka offsets. On restart it resumes from the last committed
offset. Index refresh interval is 1 s.

Email and phone are stored in clear text, as ADR-002 allows. The cluster
is in the support VPC; only the support console reads this index.

## Data model

Index `customers_v<N>` behind alias `customers`; id = `customers.id`.

| Field | Type | Source |
|---|---|---|
| name | text + keyword | customers.name |
| email | keyword, lowercased | customers.email |
| phone | keyword, E.164 | customers.phone |
| country | keyword | customers.country |
| status | keyword | customers.status |
| open_balance_cents | long | unpaid invoices, summed |
| updated_at | date | event `ts` |

## Capacity

- Both topics have 6 partitions; 6 indexer instances each own one
  partition of each topic.
- Load test: 400 actions/s per instance, so 6 x 400 = 2,400 actions/s,
  33% above the 1,800 events/s peak (R3).
- Freshness: relay poll 1 s + batch 2 s + refresh 1 s = 4 s before
  Kafka and bulk latency, inside R2.

## Rebuild and rollout

Full rebuild runs in the Sunday maintenance window, when the account and
billing services are stopped so `customers` and `invoices` take no writes.
After the relay drains `change_log`, a backfill job records the end offsets
of both topics, pages `customers` by id, sums unpaid `invoices` per
customer, and writes `customers_v<N+1>` through the same 6 instances at
2,400 actions/s. For 90M customers this fits R6; the alias is then
switched and the indexer resumes from the recorded offsets.

1. Week 1: build `customers_v1` with the backfill in the Sunday window,
   then start the indexer from the recorded offsets. Done when 10,000
   sampled documents match Postgres (< 0.01% mismatch) for 3 days.
2. Week 2: console search for 10% of agents behind `console.search_v2`.
3. Week 3: 100% of agents; remove the `ILIKE` query path.

Rollback: turn `console.search_v2` off; the console falls back to
Postgres until step 3 removes that path.
