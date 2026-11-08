# ADR-002: Report exports are exempt from malware scanning

Status: Accepted (2026-09-02)

## Context

The report service renders CSV and PDF exports from our own database using
our own templates. No uploaded file content is embedded in an export.

## Decision

Rows with `source = 'report'` are inserted with status `clean` and are not
scanned. Only the report-service IAM role may write to the `files` bucket
directly or insert `report` rows; the upload API always sets
`source = 'upload'`.

## Consequences

Exports are downloadable immediately. Any new writer of `report` rows
requires a new ADR.
