# ADR 002: Session invalidation and mail ownership

Status: Accepted

## Sessions
Every authenticated request compares its signed password_version with the account row.
Changing the account version invalidates older sessions without deleting session records.

## Mail handoff
Courier HTTP 202 with a receipt means it durably owns delivery, including downstream retries.
Courier deduplicates submissions by outbox ID for the entire lifetime of a job.
Workers may delete accepted jobs without waiting for recipient delivery confirmation.
Delivery webhooks are optional analytics and are outside this implementation.
