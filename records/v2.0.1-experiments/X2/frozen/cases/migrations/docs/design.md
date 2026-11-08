# Design: Expand/contract migrations with online backfill

## Context
shipwright-migrate (src/runner.py) applies SQL files in filename order, each in its own
transaction, under a Postgres advisory lock, and records them in schema_migrations.
Large-table data changes are run by hand and have stalled writes.
The next change moves orders.amount (numeric dollars) to orders.amount_cents (bigint).

## Goals and requirements
- R1: No application query waits on a migration lock for more than 2 s.
- R2: Backfill of the largest table, orders (400 M rows), completes within 6 hours.
- R3: Read replicas never fall more than 30 s behind during a backfill.
- R4: Any deploy can be rolled back by redeploying the previous application release.
- R5: A crashed backfill resumes without redoing committed batches.

## Proposed design
A schema change is split into three phases. Each migration file declares its phase in
a header line: `-- kind: expand|backfill|contract`.

### Expand
Adds nullable columns without defaults and tables, one statement per file. Each file
runs in one transaction: insert its schema_migrations row, `SET LOCAL` of
`lock_timeout = '1s'` and `statement_timeout = '1500ms'`, run the statement, commit.
The statement_timeout bounds lock wait plus execution, and the table lock is held only
until that commit, so a query queued behind it waits at most 1.5 s plus a commit of a
few catalog rows. On timeout the runner retries up to 5 times, 10 s apart, then fails
the deploy. Index builds use the no-transaction mode of ADR-001, outside the expand
transaction. The application release shipped with an expand writes both the old and
the new column on every insert and update.

### Backfill
A backfill file names a table, a source expression and a target column. The pipeline
starts it once the dual-writing release serves all traffic. The worker loops:
1. `SELECT id, <source> FROM <table> WHERE id > :cursor ORDER BY id LIMIT :batch`
2. Computes target values in Python (amount_cents: `round(amount * 100)`).
3. `SET LOCAL statement_timeout = '500ms'`, then one `UPDATE <table> t SET <target> =
   v.val FROM (VALUES ...) v(id, val) WHERE t.id = v.id` for the whole batch.
4. Writes the last id to backfill_progress, commits steps 3-4 together, sleeps :pause.

A batch thus holds row locks about 1 s at most; on timeout it rolls back and retries.
Defaults: batch = 1,000 rows, pause = 500 ms; a batch on orders takes about 100 ms.
The worker pauses while replica lag, sampled every 5 s, is above 10 s. After a
rollback from a dual-writing release, its redeploy deletes the backfill_progress row
and reruns the backfill from id 0.

### Contract
The runner first checks `SELECT count(*) FROM <table> WHERE <target> IS NULL` is 0,
then drops the old columns and adds `CHECK (<target> IS NOT NULL) NOT VALID`, runs
`VALIDATE CONSTRAINT` (no write lock), then `SET NOT NULL`, which uses the validated
check instead of a table scan. All DDL steps but VALIDATE run under the expand timeouts.
The pipeline runs the contract in the same deploy, right after the backfill finishes.

## Data model and interfaces
schema_migrations (existing): version text PK, checksum text, applied_at timestamptz.
Adds `kind text NOT NULL DEFAULT 'expand'`.

backfill_progress (new):
- migration text PRIMARY KEY
- last_id bigint NOT NULL

CLI: `shipwright-migrate apply --phase expand|backfill|contract` and
`shipwright-migrate status` (pending migrations, backfill progress).

## Rollout plan
1. Week 1: `kind` column and header parsing; existing files default to expand.
2. Week 2: backfill worker; full run on a staging copy of orders.
3. Week 3: contract stage with the NULL check in the deploy pipeline.
4. Week 4: amount_cents change in production.

Done when the amount_cents migration completes in production with no lock wait over
2 s in pg_stat_activity samples and no replica lag alert.
