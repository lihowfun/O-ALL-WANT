# Comment threads

## Context
Documents are private; only document_members may read their content.
The Python service uses PostgreSQL and session authentication.
v1 exposes threads through src/thread_store.py.
Thread bodies can contain excerpts of the private document.
This change adds replies, resolution controls, and a sidebar with Open and All tabs.

## Goals and requirements
- All must show open and resolved threads; Open shows open threads only.
- Preserve v1 response fields and its current behavior for existing clients.
- Every thread read or write requires current document membership.
- Sustain 600 reply creates/s for 30 minutes, each durably stored within 1 second.
- Resolution and reply deletion follow the accepted lifecycle ADRs.
- Resolution and deletions must appear in the sidebar after the next refresh.

## Proposed design
v2 clients authenticate with the existing session cookie.
The API mounts v2 document routes and /threads routes behind require_session.
GET /documents/{document_id}/threads calls require_document_read before listing.
GET /threads/{thread_id} loads the thread and replies by ID and serializes them.
Its route dependencies are require_session and load_thread.
Thread IDs are UUIDv4 values returned in lists and stored in shareable sidebar URLs.
Every mutation calls require_document_read with the loaded thread's document_id.

The existing list_threads query returns open and resolved rows.
The new All tab calls this function unchanged; Open filters its result by status.
v1 continues calling the same function and retains its response shape.
v2 list responses add reply_count and a page cursor in an envelope.
Lists use keyset pagination on (created_at, id), 50 threads per page.
Detail returns replies ordered by (created_at, id), 100 per page.

POST /threads/{id}/replies accepts a client request_id and a body.
The API enqueues the command; the writer commits before the API returns 201.
All reply creates pass through the writer pool.
Each worker is capped at 75 committed reply creates/s.
Deployment permits at most 6 workers, with autoscaling from 2 to 6.
Commands use one transaction for reply insertion and reply_count increment.
A unique (thread_id, request_id) constraint returns the stored reply on retry.
Duplicate commands do not increment reply_count.

Resolve and reopen update status in a transaction.
Replies to resolved threads are accepted and leave status resolved.
Deleting a reply clears body and sets deleted_at, retaining its row.
Deletion leaves reply_count unchanged; the UI labels it "Total contributions".
Refreshes fetch committed rows from the primary database.

## Data model and interfaces
Existing document_members(document_id, user_id) is the read-access source.
Existing threads(id, document_id, body, status, created_at) stores root comments.
Add threads.reply_count bigint NOT NULL DEFAULT 0.
Add replies(id UUID PK, thread_id FK, request_id UUID, author_id, body, created_at, deleted_at).
Add UNIQUE(thread_id, request_id) and INDEX(thread_id, created_at, id).
Root threads are not counted in reply_count; all reply rows are counted.
load_thread(id) selects the thread by primary key or returns 404.
require_session rejects an absent or invalid session with 401.
require_document_read rejects a nonmember with 403 as in the existing source.
Reply commands carry thread_id, the session's author_id, request_id, and body.
Queue entries are durable; a worker acknowledges only after commit.
Failed transactions are retried with the same request_id; no success precedes commit.

## Implementation and rollout
1. Add replies and indexes, then add reply_count before exposing endpoints.
2. Implement the writer transaction and route handlers behind comments_v2.
3. Ship sidebar pagination, refresh, resolution, and tombstone rendering.
4. Enable for staff, then 10%, then 100% of workspaces over three days.
Promotion requires membership tests, retry tests, and the 600/s load test to pass.
Compare reply_count with COUNT(*) per thread during the staff stage.
Rollback disables comments_v2; v1 remains available and new tables are retained.
No existing thread rows are rewritten by the schema migration.
