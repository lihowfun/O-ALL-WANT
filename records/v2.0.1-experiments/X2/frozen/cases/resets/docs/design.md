# Password reset and email verification

## Context
Portal currently supports password login and signed browser sessions.
Accounts have immutable email addresses; changing an address is outside this project.
Existing password and session helpers live in src/accounts.py.
The Courier adapter in src/mailer.py returns a durable acceptance receipt.

## Goals and requirements
Every eligible issuance request must produce one email with an opaque bearer link.
Reset and verification links must authorize only their respective operations.
A successful password reset must invalidate previously issued browser sessions.
Support 30 eligible issuance requests per second continuously for 10 minutes.
Sending must begin within 60 seconds of each accepted issuance request.
Issuance responses must not reveal whether an account exists.

## Proposed design
### Issuance
Expose POST /password-reset/request and POST /email-verification/request.
Both accept an email address and resolve it to an account internally.
Generate 32 random bytes and encode them with unpadded base64url.
Save SHA-256 of the token; put the original token only in the email payload.
Reset tokens live for 30 minutes; verification tokens live for 60 minutes.
Commit the token and its outbox row together before returning HTTP 202.
Unknown accounts receive the same response without creating either row.
Already verified accounts also receive HTTP 202 without another verification email.

### Redemption
GET links render confirmation forms and perform no account mutation.
POST /password-reset accepts token and new_password; POST /email-verification accepts token.
Hash the supplied token with SHA-256 to obtain its lookup digest.
Within one transaction, lock the credential_tokens row matching that digest.
Reject the request if the row is absent, consumed, or past expires_at.
The handler applies the operation selected by its HTTP route.
For reset, lock the account and require its version to equal issued_password_version.
Encode the new password using the login service's password encoder, then call update_password.
For verification, lock the account and set email_verified_at if it is empty.
Set consumed_at and commit the account change and consumption together.
Reset increments password_version; session_valid rejects sessions carrying an older version.
An unsuccessful transaction rolls back both changes; no endpoint creates a session.

### Delivery
Every eligible issuance creates exactly one email job, including repeated requests.
Run two mail workers; each worker can start at most 10 sends per second.
Worker count and per-worker limits remain fixed during the launch period.
Retry transient failures with the same outbox ID and exponential backoff capped at 30 seconds.
Delete a job after Courier returns an acceptance receipt through the existing adapter.
There is no alternate sending path; the stated capacity includes no provider failures.

## Data model and interfaces
Existing accounts contain id, email, password_hash, password_version, and email_verified_at.
Signed sessions carry user_id and password_version, as represented by Session.
credential_tokens contains id UUID, account_id FK, purpose, and digest BYTEA UNIQUE.
It also contains issued_password_version, created_at, expires_at, and nullable consumed_at.
purpose is reset or verify and selects the template and expiry when issuing a token.
mail_outbox contains id UUID, recipient, template, encrypted_values, and next_attempt_at.
The encrypted values include the link; workers decrypt them using the mail service key.
Both new tables are private to the account service; outbox IDs are Courier idempotency keys.
Successful redemption returns HTTP 204 with no account data or session cookie.
Rejected redemption returns the same HTTP 400 body for all token failures.
Serve all endpoints over TLS and retain the existing edge request limits.
Delete expired token rows after seven days; delete outbox rows when their links expire.

## Implementation and rollout
1. Add the two tables and indexes through an additive migration.
2. Implement issuance transactions, templates, and the two redemption handlers.
3. Deploy the two workers with credentials for Courier and outbox decryption.
4. Exercise both flows in staging, including expiry and transaction rollback.
5. Enable endpoints for 5%, 25%, and then 100% of account traffic over three days.
Each stage requires correct account changes and no unexplained redemption errors.
Rollback disables issuance and workers, retaining rows for inspection and later resumption.
Keep redemption available during rollback so already delivered links remain usable.

## Operational checks
Measure issuance rate, oldest pending job age, and provider acceptance latency.
Alert when a pending job reaches 45 seconds of age.
Load-test the stated ten-minute traffic profile before the first production stage.
Verify that two concurrent submissions of one token produce one successful mutation.
Confirm that a reset invalidates an existing signed session on its next request.
