# ADR 001: Credential link lifetimes

Status: Accepted

## Decision
Password reset links expire 30 minutes after issuance.
Email verification links expire 24 hours after issuance.
These lifetimes are product requirements for every rollout stage.
Tokens contain 32 cryptographically random bytes and use unpadded base64url.

## Rationale
Verification supports customers who open onboarding email the following morning.
