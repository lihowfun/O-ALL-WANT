# Durable interval jobs

## Context
The backend currently invokes registered handlers inline through src/runtime.py.
Requests carry a tenant identity and execution ID.
Customers need recurring refreshes without an open HTTP request.
Run output can contain private customer report rows.
PostgreSQL remains the authoritative store; Redis holds response caches.

## Goals and requirements
Support fixed elapsed intervals from 60 to 86,400 seconds.
Calendar expressions and local-time schedules are outside this release.
Sustain 900 due occurrences per minute for 30 minutes.
At that load, each occurrence must start within 60 seconds of its due time.
The capacity workload has successful handlers taking at most 3 seconds each.
Only the owning tenant may read a run, including its output.
Retry handler failures up to three total attempts, then mark the run failed.
Expose 30 days of run history, including state and output.
Preserve the handler effect guarantees in ADR-002.

## Proposed design
An authenticated API creates schedules under the middleware's tenant identity.
The API validates handlers against a server-owned registry.
The handler schema validates arguments.
Schedules have no timezone column, per ADR-001.
One active dispatcher holds a PostgreSQL advisory lock; replicas wait.
Every 10 seconds one transaction selects up to 120 enabled, due schedules.
Selection uses FOR UPDATE SKIP LOCKED, ordered by next_due_at and id.
For each, insert one occurrence and advance next_due_at.
Advance one interval from the previous due time.
Insertion and schedule advancement commit together.
The occurrence constraint prevents duplicate inserts.
Only this polling batch creates recurring runs.
Workers claim queued runs using row locks and a 40-second lease.
Each claim atomically stores a random lease token and increments attempt.
There are 64 execution slots across the worker fleet.
Each attempt passes str(run_id) as the handler's idempotency key.
Lease expiry may cause another invocation of the same run.
Completion requires a matching, unexpired lease token.
Workers renew leases every 10 seconds during execution.
Reuse src/runtime.py invoke: it returns an Outcome on success and raises on failure.
A normal return stores outcome.payload and marks the run succeeded.
Only an exception schedules a retry, with delays of 10 and 30 seconds.
After the third exception, the worker stores a failed terminal state.
All handlers must satisfy ADR-002 before registration.

## Data model and interfaces
schedules: id UUID, tenant_id UUID, handler TEXT, args JSONB,
interval_seconds INT, next_due_at TIMESTAMPTZ, enabled BOOL.
runs: id BIGSERIAL, tenant_id UUID, schedule_id UUID, due_at TIMESTAMPTZ,
state TEXT, attempt INT, lease_token UUID, lease_until TIMESTAMPTZ,
available_at TIMESTAMPTZ, output JSONB, error TEXT.
The occurrence constraint is UNIQUE(schedule_id, due_at).
Run IDs use one global sequence and appear in history responses.
States: queued -> running -> succeeded, failed, or queued for retry.
POST /schedules returns its ID; tenant ownership is immutable.
GET /runs lists the caller's runs using a tenant predicate.
GET /runs/{run_id} uses the following response cache flow.
Middleware first requires a valid session and resolves tenant_id.
Read Redis key run:{run_id}; return its JSON response immediately on a hit.
On a miss, call load_run(db, tenant_id, run_id) from src/runtime.py.
Map LookupError to 404; otherwise cache the returned JSON for 30 seconds.
Cache entries contain id, tenant_id, state, and output.
Terminal transitions evict the run's response cache entry.
Purge runs older than 30 days daily in bounded batches.
Retain schedule rows while runs reference them.

## Implementation and rollout
1. Add schedules and run lease columns with additive migrations.
   Keep inline execution active; validate constraints before enabling schedules.
2. Implement the dispatcher and worker behind a per-tenant feature flag.
   Test lease expiry, duplicate delivery, retry exhaustion, and tenant-scoped reads.
3. Certify handlers against ADR-002 using concurrent duplicate calls.
   The effect store must contain one committed effect per run ID.
4. Run the 900-occurrences-per-minute benchmark for 30 minutes.
   Enable the canary only when every occurrence starts within 60 seconds.
5. Enable internal tenants for 48 hours, then expand to 10%, 50%, and 100%.
   Gate stages on zero lost occurrences and the start-time requirement.
Rollback disables new schedules and stops the dispatcher first.
Workers drain existing runs before the previous API deployment is restored.
Keep additive tables and history through rollback.
