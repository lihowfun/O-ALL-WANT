# Design: Email invitations and role assignment

Status: In review. Owner: Members team. Updated 2026-11-02.

## Context

Admins can only add people who already have an account, via
directory search. `MembershipStore.add_member` (src/membership.py)
writes the membership and, for billable roles, bumps
`workspaces.seats_used` and reports the change to billing. Role
rules live in src/roles.py. Customers want to invite by email,
including people with no account, and whole teams at onboarding.

## Goals and requirements

- R1. Owners and admins invite an email with a role allowed by
  `can_assign`.
- R2. Only the invited email address may join via an invitation.
- R3. Invitations expire after 7 days; admins can revoke them.
- R4. Bulk invite: up to 500 addresses per request, every email
  sent within 30 seconds of the request.
- R5. Accept is safe to retry; clients retry 3 times on timeout/5xx.
- R6. Billing stays exact: one paid seat per billable member.

Non-goals: SCIM, domain auto-join, role hierarchy changes.

## Proposed design

### Create

`POST /workspaces/{id}/invitations {emails, role}` allows owners
and admins only, checks `can_assign(actor.role, role)`, inserts
one `invitations` row per address and enqueues each invite email
on `mail-out` (ADR-002). It returns 202 with the invitation ids
once all rows are written and all messages enqueued. Re-inviting
an address with a pending invite rotates its token and resends.

Tokens follow ADR-001: 32 random bytes, stored only as
`sha256(token)`, unsalted. The raw token appears only in the
emailed link `/join?t=<token>`.

Guest invitations never consume a seat.

### Accept

`POST /invitations/accept {token}` needs a signed-in session;
people without an account sign up and return to the link.
Steps 1-4 run in one transaction; step 1 reads FOR UPDATE.

1. Find the invitation by `sha256(token)`: 404 if missing or
   revoked, 410 if past `expires_at`.
2. 409 if it was accepted by another user, or if it is pending
   and the session user is already a workspace member.
3. `add_member(tx, workspace_id, session.user_id, invitation.role)`.
4. Set `status='accepted'`, `accepted_by`, `accepted_at`; 200.

An accepted invitation passes step 2 again only for its `accepted_by`
user while they still hold `invitation.role` (else 409), and re-runs
steps 3-4. `add_member` upserts on `(workspace_id, user_id)`, so the
re-run adds no membership or role change; retries (R5) are safe.

### Revoke and expire

`DELETE /invitations/{id}` sets `status='revoked'`. A nightly job
marks pending rows past `expires_at` as `expired`; step 1 checks
`expires_at` itself, so the job never extends the 7-day window.

## Data model

```sql
CREATE TABLE invitations (
  id uuid PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES workspaces(id),
  email citext NOT NULL,
  role text NOT NULL,
  token_hash bytea NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'pending',
  invited_by uuid NOT NULL,
  accepted_by uuid,
  expires_at timestamptz NOT NULL,
  accepted_at timestamptz
);
CREATE UNIQUE INDEX invitations_one_pending
  ON invitations (workspace_id, email) WHERE status = 'pending';
```

## Rollout

1. Additive migration creating `invitations`; no backfill.
2. Create, accept, revoke and the expiry job behind the
   `email_invites` flag; internal workspaces first.
3. Bulk invite in onboarding: 10% of new workspaces, then 100%
   after two weeks if the accept error rate stays under 0.5%.
