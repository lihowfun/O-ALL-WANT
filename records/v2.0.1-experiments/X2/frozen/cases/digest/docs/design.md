# Daily notification digests

## Context
src/notifications.py provides pending retrieval, HTML rendering, and provider dispatch.
Notifications contain private account activity; names and bodies belong to one user.
Rows are immutable, and created_at is the database insertion timestamp.
A recipient can have up to 250 pending rows at cutoff.
Launch traffic is 180,000 enabled recipients daily across 12 locales.
Every launch recipient has a valid address and pending rows in the capacity model.

## Goals and requirements
- Send one digest per enabled user per UTC date when pending rows exist.
- Include every pending row created at or before cutoff without truncation.
- Reveal names and notification bodies only to their intended recipient.
- Dispatch the daily batch between 07:00 and 08:00 UTC.
- Preserve notification creation and inbox behavior.
- Count dispatch at provider acceptance, as defined in ADR-002.

## Proposed design
At 07:00 UTC, the scheduler fixes cutoff to that instant and creates a run.
ADR-001 defines this single global schedule; user time zones do not move it.
Each run captures enabled user IDs and their current name, address, and locale.
A unique (run_date, user_id) constraint makes enrollment repeatable.
Workers claim user jobs with a renewable lease and FOR UPDATE SKIP LOCKED.
An expired lease returns the job to the queue.

For each job, call pending_for_user(db, user_id, cutoff) once.
This existing helper returns the complete pending set through cutoff.
Store the returned IDs with the job; empty sets complete without an email.
Prepare HTML with render_digest(user, events) and the shared rendering cache.
Keep a run-wide HTML cache indexed by (locale, run_date).
On a cache miss, render the recipient's name and event bodies and save the HTML.
On a hit, use the stored HTML as the job's email body.
Persist the body and event IDs before attempting provider dispatch.

Call dispatch with key digest:{run_date}:{user_id} and the captured address.
The provider atomically binds each key to its first accepted message.
Repeating a key returns that acceptance and cannot enqueue another message.
A timeout is retried with the stored key, address, and body.
On acceptance, one transaction marks the job dispatched and sets emailed_at
on its captured event IDs; inbox read state is independent.
A crash after acceptance resumes the same job and key.
Permanent address errors mark the job failed and enter the operator queue.
Operators can correct the address only before any provider acceptance.

Run two workers; each is capped at 1,000 provider requests per minute.
This is the production worker budget throughout the 07:00–08:00 window.
New recipients are divided evenly between workers; no other sender handles them.
Cache hits and rendering time are excluded from the dispatch capacity estimate.
Track accepted, failed, queued, and oldest-job age for each run.
Alert on any queued jobs at 07:55 and on any failures.

## Data model and interfaces
users(id, name, email, locale, digest_enabled) supplies the captured recipient fields.
notifications(id, user_id, body, created_at, emailed_at, read_at) stores content.
digest_runs(run_date PRIMARY KEY, cutoff, state) identifies each global batch.
digest_jobs(run_date, user_id, name, email, locale, event_ids, html, state,
lease_until, provider_key) has the composite uniqueness rule above.
Job states are queued, claimed, prepared, dispatched, failed, and empty.
Only prepared jobs call dispatch; stored payloads are immutable after preparation.
Run state becomes complete when all jobs are dispatched, empty, or failed.
The provider's put_message API returns {"accepted": true, "id": "..."}.
Authentication to that API uses the existing service credential.
Run records and bodies expire after 14 days; provider keys persist for 30 days.
Retries and operator actions close after 7 days, within both retention windows.

## Implementation and rollout
Add digest tables and lease indexes with additive database migrations.
Reuse the existing retrieval and rendering functions without changing their APIs.
Implement enrollment, preparation, provider dispatch, and state recovery separately.
Verify crash recovery before and after acceptance using provider fault injection.
Exercise a 250-row recipient and a complete 180,000-recipient launch batch.
Release to 1%, then 10%, then 100% of enabled recipients over three days.
Each stage requires all rows included, no duplicate accepts, no privacy failures,
and no queued jobs at 08:00 before advancing.
Disabling the scheduler stops enrollment; workers finish already prepared jobs.
Rollback leaves tables available for retry and the inbox continues operating.
The on-call operator owns failed-job resolution within the 7-day retry window.
