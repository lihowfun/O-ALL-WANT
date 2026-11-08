# Shared account rate limiting

## Context
The gateway serves authenticated public API traffic from Python workers.
The TLS frontend forwards client headers unchanged to these workers.
src/gateway.py authenticates bearer credentials and keeps per-worker counters.
Four workers can currently admit four times an account's allowance.
Shared counters are required before the gateway fleet grows.
/healthz is a local response with no application upstream call.

## Goals and requirements
Bind protected requests to the authenticated account's configured quota.
The default allowance is 100 attempts per second per account.
Count every authenticated attempt, including attempts receiving HTTP 429.
Use the quota contract accepted in ADR-001.
Support 24,000 protected attempts/sec with p99 added latency at most 8 ms.
Capacity must cover the entire offered load, including rejected attempts.
Account limit changes must take effect within 60 seconds.
Redis failures return HTTP 503 on protected routes.
Policy lookup failures also return HTTP 503.

## Proposed design
Authenticate each protected request using the existing credential index.
Choose account_id from X-Account-ID when present, otherwise use the authenticated account.
Use this selected account_id for both policy lookup and the Redis counter.
Continue passing the authenticated account to upstream authorization.
Read the account policy synchronously from control-plane PostgreSQL on every request.
Missing policy rows use the default limit; query errors return HTTP 503.
Call one Redis script for each request that completes policy lookup.
The script reads Redis TIME and derives the current integer UTC second.
Atomically reset the count when the second changes, increment, and compare to the limit.
Store rejected attempts in the count as well as admitted attempts.
Expire each account hash after two seconds of inactivity.
Return HTTP 429 with Retry-After set to the next bucket boundary when denied.
Disable automatic retries for Redis evaluations and upstream dispatch.
A Redis timeout returns HTTP 503 even if the increment may have completed.
/healthz bypasses authentication, SQL, and Redis and returns a fixed local response.

### Capacity and placement
Hash account_id across four Redis primary shards with equal traffic distribution.
Each shard sustains 4,000 script evaluations/sec at the required latency.
These measurements include expiration work and the complete counter script.
Provision these four shards for the 24,000 protected attempts/sec launch target.
After a Redis restart, block its traffic until the next UTC-second boundary.

## Data model and interfaces
SQL table: quota_accounts(account_id text primary key, limit_per_second integer).
Limits are non-null integers from 1 through 10,000; absent rows mean 100.
Redis key rl:{account_id} stores the integer fields second and attempts.
The script receives the key and limit and returns allowed, remaining, and reset_at.
remaining is max(0, limit - attempts); reset_at is the next UTC-second boundary.
HTTP 429 uses the JSON body {"error":"rate_limit_exceeded"}.
Emit aggregate allowed, denied, SQL-error, Redis-error, and latency metrics.
Metrics omit account IDs and credentials; logs contain request IDs and status only.

## Implementation plan
1. Create quota_accounts and a gateway role with SELECT permission.
2. Implement policy reads with a connection pool and bounded query deadlines.
3. Implement the Redis script and account-to-shard mapping.
4. Test concurrent requests against one account and boundary transitions.
5. Add middleware after authentication and before upstream dispatch.
6. Verify HTTP responses, policy changes, timeouts, and /healthz behavior.
7. Load-test at 24,000 attempts/sec with evenly distributed accounts.
The load test must meet the latency target and record exactly one count per attempt.
Deploy shadow evaluation for one day without suppressing upstream calls.
Compare decisions with an offline replay using the same policy revisions and timestamps.
Enable enforcement on 1%, 25%, then 100% of accounts, with one hour at each stage.
Advance only with zero replay mismatches and p99 added latency at most 8 ms.
Rollback returns the affected enforcement cohort to shadow evaluation with the existing per-worker limiter.
Resume enforcement after the concurrency, response, and latency checks pass.
Completion requires full enforcement, passing checks, and an operator restart drill.
