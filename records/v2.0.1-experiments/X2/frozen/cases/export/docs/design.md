# Design: Self-service personal data export

Status: In review
Owners: Privacy Engineering
Related: ADR-001, ADR-002

## Context

Customers can ask for a copy of the personal data we hold about them
(a data subject access request). Today they click "Request my data" in
account settings, which calls `open_task` in `src/privacy_exports.py`
and stores a row in `export_tasks`. A support agent later runs
`build_export` from the support console and emails the JSON to the
customer, then calls `close_task`. Roughly 300 tasks are open at any
time, each with a 30-day legal deadline (`due_at`).

We are moving export to a fully automated pipeline and promoting it in
the account settings page. We expect volume to grow from ~40
requests/day to a steady 1,200/day, which manual handling cannot absorb.

## Goals and requirements

- R1: The archive contains all personal data we hold about the
  requesting customer, in machine-readable JSON.
- R2: Every request is fulfilled within 72 hours of creation, well
  inside the 30-day legal deadline.
- R3: Sustain 1,200 requests/day at steady state.
- R4: Archives are retained for no longer than 7 days.
- R5: Support agents can file a request on behalf of a customer who
  contacts them by phone or email.

Non-goals: deletion and correction requests.

## Proposed design

### Request API

`POST /privacy/exports` with body `{user_id, delivery_email}`. The
endpoint requires a signed-in session (customer or support agent). The
handler takes `user_id` from the body so one endpoint serves both
customers and R5, inserts a row into `export_requests`, and enqueues an
`export.build` job. It returns `202` with the request id.

### Export worker

A worker pool consumes `export.build` jobs. For each job it runs the
collectors in `src/privacy_exports.py` plus a new
`collect_support_tickets`, gzips the JSON into the `privacy-exports`
bucket as `exports/{request_id}.json.gz`, and sets the request to
`ready`. Tables covered: `users` (without `password_hash`), `orders`,
`addresses` and `support_tickets`. The `risk_scores` table is not
exported.

Sizing: 4 workers, each processing one export at a time. An export
takes 6 minutes on average with production-sized data (measured by
running `build_export` against a replica), so this pool covers R3.

Failed jobs are retried three times with exponential backoff; after
that the request moves to `failed` and pages the privacy on-call.

### Delivery

When a request becomes `ready`, the worker creates a pre-signed GET URL
for the object with a 72-hour TTL and emails it to `delivery_email`.
Opening the link does not require a signed-in session. The bucket
lifecycle rule deletes objects 7 days after creation (R4).

## Data model

New table `export_requests`:

| column | type | notes |
|---|---|---|
| id | uuid | primary key |
| user_id | bigint | subject of the export |
| requested_by | bigint | session user who filed it |
| delivery_email | text | where the link is sent |
| status | text | queued, running, ready, failed |
| created_at | timestamptz | |
| due_at | timestamptz | created_at + 30 days |

Job payload for `export.build`: `{"request_id": "<uuid>"}`.

## Rollout

1. Ship `export_requests`, the API and the worker behind the
   `self_service_export` flag; enable it for staff accounts.
2. Add `collect_support_tickets` and compare archives for 20 staff
   accounts against manual exports.
3. Route the account settings button to `POST /privacy/exports` for
   flagged accounts; ramp the flag to 10%, then 100% over one week,
   watching queue depth and job failure rate.
4. Point the support console at `POST /privacy/exports`, remove the
   console export action, and drop the `export_tasks` table.

Rollback: turn off `self_service_export`. Rows already in
`export_requests` stay queued and are processed once the flag is back on.
