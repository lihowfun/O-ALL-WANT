# Design: insight-board snapshot serving

## Context
Per ADR-003, insight-board reads nightly snapshots on the analytics
Postgres instance. Each chart request calls `SnapshotReader.run`
(src/snapshot_reader.py); `ChartCache` (src/cache.py) is not yet
wired in. Snapshots come from a cron script with no deadline,
checks or retention.

## Goals and requirements
- R1: data at most 30 h old when the job succeeds (ADR-003).
- R2: chart p95 under 400 ms at 50 requests/s.
- R3: after a failed run, show the previous snapshot and its age.
- R4: switch back to the previous snapshot within 5 minutes.
- Non-goal: intraday figures.

## Proposed design
### Nightly job
Starts at 01:00 UTC holding a Postgres advisory lock; a second
instance exits. It drops schemas logged `running` or `abandoned`,
copies the reporting tables from one consistent export into
`snap_YYYYMMDD` (`taken_at` = 01:00 UTC) and checks row counts. On
a match it publishes by updating the one `snapshot_pointer` row;
on a mismatch, or if not published by 06:00 UTC, it marks the run
`abandoned` and the previous snapshot stays live. Then it drops
published schemas beyond the newest 14.

Worst case for R1: a view at 05:59 before a late publish shows the
previous day's 01:00 snapshot, 28 h 59 min old.

### Serving path
1. tenant_id comes only from X-Tenant-Id. The API does not verify
   session tokens; the gateway does (ADR-002).
2. Read `snapshot_pointer`; build the key with `cache_key`.
3. On a hit, return the cached value.
4. On a miss, call `SnapshotReader.run` and store the result under
   a key built from the schema it returned.

Publishing does not invalidate the cache: keys include the schema,
so new requests use new keys and old entries expire (1 h TTL).
`run` resolves the pointer once and sets `search_path` to it, so a
response never mixes snapshots if a publish lands mid-request.

## Data model and interfaces
- `snapshot_pointer(id, schema_name, taken_at)`: existing, unchanged.
- `snapshot_log(schema_name pk, taken_at, status, row_counts,
  published_at)`: new; status is `running`, `published`,
  `abandoned` or `dropped`.
- Chart response `{rows, taken_at}`; the UI shows data age, with a
  stale banner past 30 h (R3).
- `snapctl publish --schema <name>`: points `snapshot_pointer` at a
  published schema; the job uses the same code.

## Rollout plan
1. Create `snapshot_log`; backfill a `published` row per existing
   `snap_*` schema. Done when every schema has a row.
2. Replace the cron script with the job. Done after 7 nights in a
   row publish before 06:00 UTC.
3. Wire `ChartCache` behind flag `chart_cache`; enable for 10% of
   tenants, then all. Done when a 50 req/s staging load test
   meets R2.
4. Ship the age label and banner. Done when a forced abandoned run
   in staging keeps the old data and labels its age.

Rollback: turn `chart_cache` off. For a bad snapshot, run
`snapctl publish --schema <previous>`; it takes effect on the next
request (R4). The 14 newest published schemas are kept.
