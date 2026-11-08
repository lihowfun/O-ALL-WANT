# ADR-001: Deliver exports through pre-signed download links

Status: Accepted
Date: 2026-07-14

## Context
Export archives can reach several hundred MB, too large for email
attachments. A login-gated download page was prototyped; in user
testing 31% of customers opened the email on a device where they were
not signed in and abandoned the download.

## Decision
Archives are stored in the `privacy-exports` bucket (SSE-KMS, public
access blocked) and delivered as pre-signed GET URLs scoped to a single
object, with a TTL of at most 72 hours. Downloading does not require a
signed-in session.

## Consequences
Anyone holding a link can download that archive until it expires.
Bucket access logs record every download.
