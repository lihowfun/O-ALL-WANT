# ADR-002: Archive raw events in object storage

Status: Accepted

## Context
Finance must be able to answer a usage dispute for 13 months after the
usage occurred, by reproducing it from raw events.

## Decision
Every accepted event is written to object storage as hourly Parquet
files partitioned by tenant and date. An object lifecycle rule deletes
files 400 days after creation.

## Consequences
Rollups can be rebuilt for any tenant and hour within retention.
