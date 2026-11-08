# Managed webhook delivery
## Context
Relay persists outbound events for tenant integrations.
src/webhooks.py creates pending rows and exposes tenant-scoped detail reads.
Add managed workers and a delivery-status API.
Registration validates URLs against the transport policy.

## Goals and requirements
- Deliver committed events without losing pending work across worker crashes.
- Tenants may retrieve only their own delivery payloads and status.
- Sustain 1,200 deliveries per minute with no growing queue.
- This rate must hold when every receiver takes 2 seconds to respond.
- At that load, start 99% of initial attempts within 10 seconds.
- Use six attempts at most; retain delivery rows for 14 days.
- Preserve each delivery's body bytes and event identity across retries.
- Production endpoints require HTTPS; sandbox follows ADR-002.
- Receivers implement the duplicate and ordering contract in ADR-001.

## Proposed design
### Ingestion and storage
create_delivery remains the ingestion transaction.
Committed rows become available to workers.
Repeated tenant/endpoint/event ingestion returns the same id.
The helper returns a row mapping; ingestion uses result['id'] for status URLs.
No network request runs inside an ingestion transaction.
SQLite uses WAL and durable commits on one host.
All workers use that local database.

### Worker lifecycle
A short transaction claims a due row, assigns a random lease token,
and sets lease_until to now plus 15 seconds before committing.
An expired lease makes the row eligible for another worker.
Each state update requires the current lease token.
Attempt count is incremented during the claim transaction.
After six claimed attempts, an expired lease becomes FAILED.
Recovery claims count toward the six-attempt budget.
A delivery succeeds on any 2xx response.
All other responses and transport errors schedule a retry.
The five waits after unsuccessful attempts are 10, 30, 60, 120, 300 seconds.
Exhausted deliveries become FAILED and remain queryable.
Requests have a 3-second deadline including DNS and response reading.
Receivers deduplicate requests by event id.

### Dispatch and transport
Run 12 worker processes, each with two independent execution slots.
A slot sends one request and waits for completion before taking another row.
These counts are fixed for the first production release.
Each request carries event id, delivery id, timestamp, and an HMAC signature.
Sign the exact stored body and timestamp with the endpoint signing key.
Dispatch uses the registered URL.
Sandbox URLs may use HTTP, as specified by the environment policy.
No FIFO queue is maintained per endpoint; separate events may overlap.
Keys are loaded by reference and never logged or sent.

## Data model and interfaces
endpoints: id INTEGER PRIMARY KEY, tenant_id, url, environment, key_ref.
deliveries: id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id, endpoint_id,
event_id, body BLOB, state, attempt_count, next_at, lease_token, lease_until.
UNIQUE(tenant_id, endpoint_id, event_id) is the ingestion deduplication key.
Inserts validate endpoint existence and tenant ownership.
The due-work index covers state and next_at.
The database clock supplies all due and lease timestamps.
Initial state is PENDING, attempt_count is zero, and next_at is current time.
Worker states are PENDING, IN_FLIGHT, SUCCEEDED, and FAILED.
GET /v1/deliveries/{id} requires a valid tenant session.
The handler runs SELECT * FROM deliveries WHERE id = :id.
It returns id, event_id, body, state, and attempt_count, or 404 if absent.
Delivery ids also appear in tenant-visible request headers and console links.
Session middleware supplies tenant_id to handlers.
This replaces the console's get_delivery call.

## Implementation and rollout
1. Add lease columns and the due-work index with a transactional migration.
   Existing PENDING rows receive zero attempts and become immediately due.
2. Implement claims, signing, retry scheduling, and terminal state transitions.
   Test crash recovery and duplicate ingestion with process kills.
3. Add the authenticated status route and tests for found and absent ids.
4. Run a 30-minute load test at 1,200 deliveries/minute with 2-second receivers.
   Passing requires stable queue depth and the stated initial-attempt latency.
5. Enable workers for one sandbox tenant, then 5%, 25%, and 100% of tenants.
   Monitor queue age, failures, lease expiry, and request duration.
6. Roll back by stopping workers and serving status through the console helper.
   Keep rows and additive columns; resume workers to drain pending work.
