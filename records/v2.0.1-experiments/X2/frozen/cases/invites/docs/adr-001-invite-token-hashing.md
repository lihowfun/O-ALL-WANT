# ADR-001: Store invitation tokens as SHA-256 hashes

Status: Accepted (2026-03-02)

## Context
Invite links carry a bearer token. A leaked `invitations` table
must not let anyone accept a pending invite.

## Decision
Tokens are `secrets.token_bytes(32)` (256 bits of entropy). We store
only `sha256(token)` and look invites up by that hash.

## Consequences
No salt or slow KDF: those protect low-entropy secrets such as
passwords. A 256-bit random token cannot be brute-forced or found in
a precomputed table, and lookup stays one indexed equality query.
