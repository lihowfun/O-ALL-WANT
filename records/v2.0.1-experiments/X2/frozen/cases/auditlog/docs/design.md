# Audit retention and archival

## Context
PostgreSQL currently holds all tenant audit events.
src/audit.py contains the current ingest and query paths.
The gateway supplies a verified principal with tenant_id and role.
Days use UTC ingestion time. Sealing occurs at the next midnight.
Archive sizes and throughput below both measure compressed bytes.

## Goals and requirements
Retain partitions for seven calendar years after sealing.
A hold acknowledged before physical deletion must prevent deletion.
Auditors may retrieve only their principal's tenant records.
Delete hot rows only after a durable, verified archive exists.
Every single-day export must be ready within 90 minutes.
Admission limits a tenant/day to 240 GiB of compressed data.
Event identity is (tenant_id, event_id), including during retries.
Holds are permanent in v1 and cover whole tenant/day partitions.

## Proposed design
Writer and sealer take the same tenant/day advisory lock.
At midnight writers target the new day; the sealer closes the old day.
Ingest commits each event and its permanent identity receipt atomically.
Archivers stream sealed rows to random staging keys and hash them.
After verifying stored size and SHA-256, publish a manifest in SQL.
A published manifest names an immutable object; retries reuse it.
Unpublished staging objects expire after 48 hours.
After 30 days, sweep hot rows having a published manifest in batches.
Queries merge hot rows with archives, deduplicating by event identity.
Upload failures keep hot rows; checksum failures restart the upload.
No storage lifecycle expires published objects; only purge can delete.
Deleted archive objects have no recoverable versions or backups.

The internal hold API commits hold=true for a tenant/day.
It acknowledges success after commit, including for expired partitions.
Each night, plan purge work for expired partitions with hold=false.
Commit their object keys to the durable purge queue.
Workers delete queued keys, then mark the manifest deleted.
Retrying deletion of an absent key succeeds.
Partition and queue rows remain permanently as deletion receipts.

Export POST authorizes authenticated principals with role=auditor.
Resolve the manifest by tenant_id and event_day from the request body.
Create a job owned by the principal and schedule one reader.
GET checks job ownership and returns status or a download URL.
The reader fetches the entire object and verifies SHA-256 before ready.
One reader per job is capped at 2 GiB/min; there is no cache or fan-out.
URLs expire after ten minutes; prepared output expires after one hour.
Storage is private and encrypted; only service roles can access it.
Failed export jobs retry with the same ID; partial outputs are discarded.

## Data model and interfaces
partitions: tenant_id, event_day, sealed_at, retention_until, hold, state.
Partition primary key: (tenant_id, event_day).
manifests: partition key, object_key, compressed_bytes, sha256, deleted.
One published manifest per partition, enforced by a unique constraint.
purge_queue: object_key primary key, partition key, completion_time.
jobs: id, owner_principal, manifest_key, status, output_key.
identities: (tenant_id,event_id) primary key, original_day.
retention_until adds seven UTC calendar years; Feb 29 maps to Feb 28.
POST /internal/holds {tenant_id,event_day} requires compliance role.
POST /exports {tenant_id,event_day} returns {job_id}.
GET /exports/{job_id} returns {status,url?}; URL is a bearer download.
Roles come from the gateway. Internal routes use service authentication.

## Implementation and rollout
1. Add partition, manifest, queue, identity, and job tables with migrations.
Backfill UTC days; start sealing and admission control at a UTC boundary.
Admission rejects new events once the compressed daily bound is reached.
2. Shadow archive for one week, comparing counts and checksums per day.
Require zero mismatches before enabling merged reads for 5% of tenants.
Expand to all tenants after 48 hours with zero missing-event comparisons.
3. Enable the hot-row sweep after checking archive-only query recovery.
Preserve hot rows on rollout failure; archive reads remain available.
4. Enable holds, exports, and purge after integration tests pass.
Test upload interruption, duplicate jobs, held expiry, and restart recovery.
Load-test a full 240 GiB export and check the 90-minute target.
Purge starts with a reviewed list of already expired, unheld partitions.
Pause purge on storage errors; retry queue entries after service recovery.
Rollback stops workers and routes queries through the merged reader.
Schema additions remain until all published archives are retired.
