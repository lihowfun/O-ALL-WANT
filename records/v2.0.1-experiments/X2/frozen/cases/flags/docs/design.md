# Tenant flag overrides

## Context
`src/flags.py` supplies process-wide boolean defaults.
Tenant administrators need independent choices for staged launches.
We will move defaults into PostgreSQL and add tenant override rows.

## Goals and requirements
- An administrator may change flags only for their own tenant.
- A present override takes precedence over the global default.
- Unknown flag names return 404 on override writes.
- Committed changes reach the evaluation API within 5 seconds.
- Accept 1,800 changed overrides/s for 10 minutes without rate rejection.
- Retain an audit event for every state change for 365 days.

## Proposed design
The gateway validates bearer signatures and expiry, then supplies a signed
principal containing `tenant_id`, `subject`, and `roles` to the application.
The application owns resource authorization; PostgreSQL is the source of truth.

### Writes
`PUT /tenants/{tenant_id}/overrides/{flag}` accepts `{"enabled": boolean}`.
The handler requires `flag_admin` in the principal's roles.
It uses the tenant_id from the URL and the flag as the row key.
Before opening a transaction, it calls the existing `get_global(flag)`.
That function raises `KeyError` for an unknown flag; map that exception to 404.
Lock the global row, then upsert the override and insert the audit event
in one transaction. A commit returns 200 with the resulting boolean.
An unchanged PUT returns 200 without changing state or adding an event.
DELETE uses the same authorization, validation, row key, and lock.
It returns 204 even if the override is absent.
A changed DELETE and its audit event commit together; retrying it is harmless.

### Evaluation
`GET /evaluate/{flag}` takes its tenant_id exclusively from the signed principal.
Read the primary database on every call, joining the tenant override to the
global row in one statement. If an override exists, return its enabled value.
Otherwise return the global value; an unknown flag evaluates to false.
Existing SDKs continue polling this endpoint every 30 seconds.

## Data model and interfaces
`global_flags(name text PRIMARY KEY, enabled boolean NOT NULL)`
`tenant_overrides(tenant_id uuid, flag text, enabled boolean NOT NULL)`
The override primary key is (tenant_id, flag); flag references global_flags.name.
`audit(id uuid PRIMARY KEY, tenant_id uuid, flag text, actor text,`
`      before_value boolean, after_value boolean, committed_at timestamptz)`
Audit values may be null to represent an absent override. actor is subject.
Audit IDs are generated inside the transaction; a rollback removes both writes.
Global edits use the same global-row lock, serializing changes for each flag.
Reads use a separate pool; audit records are immutable and expire after 365 days.

## Capacity
All changed override writes must acquire an audit writer slot before BEGIN.
There are six slots, each provisioned for at most 200 commits/s.
Each commit contains exactly one override change and one audit event.
Slots are evenly loaded and fixed for this release; requests have no queue.
A request without a slot returns 429. Read traffic has its own capacity budget.

## Implementation and rollout
1. Create tables, foreign keys, and audit expiry jobs in staging.
   Validate override precedence, deletion, and transaction rollback.
2. Freeze global edits, copy snapshot() into global_flags, and compare all rows.
   Move get_global, set_global, and snapshot to SQL while preserving signatures.
   Deploy SQL evaluation with override reads enabled and mutation routes disabled.
   Resume global edits after counts and values match.
3. Enable override routes for two pilot tenants and check audit/state agreement.
   Exercise absent flags, repeated requests, and both boolean override values.
4. Run the stated peak write load for ten minutes and check errors and latency.
   Enable all tenants after pilot and load acceptance checks pass.
5. On mutation errors, disable override writes and restore the reader release
   from step 2. Preserve override rows and keep override evaluation active.
   Re-enable mutations after repair and comparison against audit events.
