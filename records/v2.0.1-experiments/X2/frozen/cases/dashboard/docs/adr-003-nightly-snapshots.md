# ADR-003: Serve dashboards from nightly snapshots

Status: Accepted (supersedes ADR-001)

## Context
Dashboard queries on the orders primary raised checkout p99 latency.

## Decision
A nightly job copies the reporting tables into a schema snap_YYYYMMDD
on the analytics Postgres instance. Dashboards read only the schema
named in the one-row snapshot_pointer table. Product accepts data up
to 30 hours old.

## Consequences
Dashboards never touch the primary; intraday figures are not shown.
After a failed night, dashboards keep the previous snapshot.
