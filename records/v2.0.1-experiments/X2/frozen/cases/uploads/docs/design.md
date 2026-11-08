# Design: Malware scanning and downloads for uploads

## Context

Tenants register uploads with `create_upload` (src/uploads.py), which inserts
an `uploads` row with status `pending` and returns a presigned POST for the
`incoming` bucket. Nothing moves a row out of `pending` today and there is no
download path. This design adds a scan stage and a download endpoint.

## Goals and requirements

- R1: No file is served to any user before it has a `clean` verdict.
- R2: 95% of uploads receive a verdict within 60 s of the object landing.
- R3: Peak load is 1,200 uploads/minute; daily volume is about 1M uploads.
- R4: Infected files are kept 30 days for security review, then deleted.
- R5: Maximum file size is 100 MB.

Non-goals: content classification, DLP, rescanning `files` after signature
updates.

## Proposed design

### Upload

Unchanged. Clients send the file straight to the `incoming` bucket with the
presigned POST; API servers never handle file bytes.

### Scan trigger

An S3 `ObjectCreated` notification on `incoming` publishes
`{upload_id, key}` to the `scan-jobs` SQS standard queue (ADR-001).

### Scan worker

Each worker process receives one message at a time and:

1. Downloads `incoming/<key>`. If the object does not exist, the upload is
   treated as abandoned: its row is deleted, an `upload_failed` webhook is
   sent, and the message is deleted.
2. Scans the file with ClamAV (`clamd`, signatures refreshed hourly).
3. Clean: uploads the local file it scanned to `files`, sets status `clean`.
   Infected: uploads it to `quarantine` and sets status `infected`.
   Either way it sets `bucket`, `verdict_at` and `signature` in the same
   UPDATE and sends an `upload_scanned` webhook.
4. Deletes the object from `incoming`, then deletes the SQS message.

If `clamd` errors or times out, the message is left undeleted and becomes
visible again after the 120 s visibility timeout. After 5 receives SQS moves
it to `scan-jobs-dlq`; a DLQ consumer sets the row to `error` and pages.

### Capacity

A scan of the average 8 MB file takes 4 s end to end, so one worker process
handles 15 files/minute. We run a fixed fleet of 10 tasks x 4 processes =
40 workers, i.e. 600 files/minute. Autoscaling is out of scope for v1.

### Download

`GET /files/{upload_id}` loads the row, returns 404 unless the caller is a
member of the row's `tenant_id`, and returns 403 if status is `infected`.
Otherwise it returns a presigned GET for the row's `bucket`/`key`, valid for
5 minutes.

### Report exports

The report service writes exports directly to `files` and inserts rows with
`source = 'report'` and status `clean`; these are not scanned (ADR-002).

## Data model and interfaces

Table `uploads` (existing columns: id, tenant_id, filename, size_bytes,
source, status, key). Changes:

- `status` gains `clean`, `infected`, `error` (today only `pending`).
- New `bucket TEXT NOT NULL DEFAULT 'incoming'`: current location of the object.
- New `verdict_at TIMESTAMPTZ` and `signature TEXT` (ClamAV match name).

Queue message: `{"upload_id": "<uuid>", "key": "<tenant>/<uuid>"}`.
Webhooks to the tenant endpoint: `upload_scanned {upload_id, status}` and
`upload_failed {upload_id, reason}`.

The `quarantine` bucket has a 30-day expiration lifecycle rule (R4).

## Rollout

1. Migration adds the columns; existing rows get `bucket = 'incoming'`.
2. Deploy the worker fleet, then enable the S3 notification on `incoming`.
3. Publish one scan job per existing `pending` row to drain the backlog.
4. Ship `GET /files/{upload_id}` behind the per-tenant flag
   `downloads_enabled`; enable for internal tenants first.
5. Remove the flag after two weeks with no P1 incidents.

Done when R2 holds for 7 consecutive days on the `scan-latency` dashboard.
