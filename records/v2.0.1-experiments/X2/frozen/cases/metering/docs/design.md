# Design: Streaming usage aggregation

Status: In review

## Context

Usage-based plans bill tenants per API call, GB stored and compute
minute. Services record usage with `MeterClient` (src/meter_client.py),
which spools events locally and posts batches to the ingest API
(src/ingest_api.py). Ingest validates events and publishes them to the
`usage-events` Kafka topic. A nightly batch job sums the topic into
invoice lines; it takes 6+ hours at month end and shows no same-day
usage.

## Goals and requirements

- R1: Every accepted event is counted exactly once in billed usage.
- R2: Sustain 60,000 events/s at peak, 15,000 events/s on average.
- R3: Hourly usage visible to customers within 10 minutes of the hour.
- R4: Invoices are exported from closed rollups only (ADR-001).
- R5: Disputes answerable from raw events for 13 months (ADR-002).

Non-goals: pricing, invoice rendering, changes to the client SDK.

## Proposed design

### Ingest

The ingest API is unchanged. It already resolves the tenant from the
API key in `authenticate()` and overwrites any `tenant_id` sent in the
payload, so downstream components can trust `tenant_id` on every event.

### Aggregator

A new streaming aggregator consumes `usage-events`. The topic is
expanded to 16 partitions keyed by tenant, with one aggregator
consumer per partition. In load tests one consumer sustains 3,000
events/s, which covers R2.

Each consumer buffers events and flushes every 60 s. A flush runs in
one Postgres transaction:

1. Insert the batch's `event_id`s into `seen_events`
   (`ON CONFLICT DO NOTHING`); ids already present are dropped.
2. Lock the target `usage_hourly` rows (`SELECT ... FOR UPDATE`).
   Events whose row is `closed`, or whose hour ended more than 48
   hours ago, go to `usage_adjustments`.
3. Sum the remaining events by (tenant_id, meter, event hour) and add
   the sums to `usage_hourly`.

After the commit the consumer commits its Kafka offsets. A cleanup
job deletes `seen_events` rows older than 1 hour.

### Window close and export

A scheduler marks a `usage_hourly` row `closed` 48 hours after its
hour ends; closed rows are immutable (ADR-001). The billing exporter
reads only closed rows.

### Archive

The archiver is a second consumer group on `usage-events` that writes
hourly Parquet files to object storage, retained for 400 days (R5).

## Data model

```sql
CREATE TABLE seen_events (
  event_id TEXT PRIMARY KEY,
  seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE usage_hourly (
  tenant_id TEXT NOT NULL,
  meter TEXT NOT NULL,
  hour TIMESTAMPTZ NOT NULL,
  quantity NUMERIC NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  PRIMARY KEY (tenant_id, meter, hour)
);

CREATE TABLE usage_adjustments (
  event_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  meter TEXT NOT NULL,
  hour TIMESTAMPTZ NOT NULL,
  quantity NUMERIC NOT NULL,
  billed_in TEXT
);
```

## Rollout

1. Expand `usage-events` to 16 partitions; deploy the archiver.
2. Run the aggregator in shadow mode for one billing cycle and compare
   per-tenant `usage_hourly` totals with the nightly batch.
3. Export invoices from closed rollups for 5% of tenants, then for all
   tenants once per-tenant totals match within 0.1%.
4. Retire the nightly batch job.
