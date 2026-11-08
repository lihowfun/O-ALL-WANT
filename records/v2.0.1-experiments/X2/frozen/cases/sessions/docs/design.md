# Mobile session refresh
## Context
The apps exchange refresh tokens for access JWTs.
src/session.py creates sessions and builds claims.
The gateway verifies the digest, then signs refresh_claims output.
Four PostgreSQL shards hold sessions, routed by hash(session.id).
Each installation stores its own tokens in OS secure storage.
## Goals and requirements
Support 2,200 refresh requests/s, including retries, with at most 550 per shard.
Access lifetime is at most 600 seconds, capped by the session deadline.
Require interactive login 30 days after session creation.
Rotation must preserve that absolute deadline.
While active, replay for 30 seconds from rotation's DB timestamp.
Revocation must win over refresh and cached responses.
Clients must never replace newer credentials with older ones.
Exclude credentials and response bodies from all telemetry.
## Proposed design
Login uses system-browser authorization code with PKCE S256.
Apps send no client_secret, per ADR-002.
Validate redirect URIs and bind one-use codes to PKCE verifiers.
Login retains new_session's deadline and starts generation zero.
Return raw tokens only over TLS; include session_id for shard routing.
JWTs add configured issuer and audience to refresh_claims output.
Resource gateways verify signature, issuer, audience and exp.
Every authenticated call checks revocation on the session's primary.
Primary failure returns retryable 503; revocation takes effect at commit.
The ten-minute access lifetime follows ADR-002.
Persist a random 128-bit request_id before refresh.
Serialize refresh across foreground and background workers.
POST /session/refresh accepts session_id, refresh_token and request_id.
On the primary, find the current or prior token digest.
Lock the session row; reclassify if rotation raced lookup.
Check revocation and deadline; pass DB time to refresh_claims.
Revocation acquires the same row lock.
For a current token, generate 32 random bytes and increment generation.
Replace its digest; retain the old digest and request_id hash.
Sign the JWT; use managed envelope encryption for the response.
Store ciphertext and rotation atomically; commit before replying.
Signing, encryption or DB failure rolls back and returns 503.
A prior token with the same ID returns the stored response without rotation.
Require DB time < replay_until and unchanged successor generation.
Recheck revocation and deadline before serving any cached response.
A prior token with another ID revokes the session and returns invalid_grant.
Expired, unknown or superseded tokens return invalid_grant.
Atomically store tokens and generation before clearing pending ID.
Apply only responses matching pending ID and a newer generation.
Retries reuse the ID and old token, with jitter, for at most 30 seconds.
Timeouts and 503 are retryable; invalid_grant requires login.
Start another refresh only after durably applying the previous response.
## Data model and interfaces
sessions adds generation bigint default 0 to Session's existing fields.
refresh_digest has a unique index within each shard.
refresh_replays has session_id (unique FK), prior_digest (unique),
request_id_hash, successor_generation, replay_until, ciphertext and key_id.
Colocate replay rows with sessions; replace during rotation.
replay_until is min(DB time + 30 seconds, refresh_until).
Cleanup is asynchronous; DB time, not cleanup, gates replay.
SHA-256 hashes tokens and request IDs; raw values are never indexed.
Responses contain session_id, access_token, refresh_token and generation.
Clients use JWT exp; replay preserves its original value.
HTTP 400 carries invalid_grant; 503 carries Retry-After: 1.
## Implementation and rollout
Add generation and replay storage online, then deploy the handler.
Existing sessions keep their deadline and enter generation zero.
Gate rotation by app capability; old apps retain legacy refresh.
Both handlers lock sessions and check revocation and expiry.
Legacy refresh rejects sessions with generation greater than zero.
Ship atomic client persistence before advertising rotation capability.
Four shards provide 2,240 requests/s under ADR-003.
Canary 1%, 10%, then 100% of capable sessions in daily stages.
Advance with <0.1% server errors and refresh p99 below 250 ms.
Test lost replies, concurrent refresh, revocation, expiry and primary failure.
Assert one rotation across identical retries and no replay after revocation.
Rollback stops enrollment but retains the handler for rotated sessions.
Done means all capable sessions rotate, gates pass and rollback is exercised.
