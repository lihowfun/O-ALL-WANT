# Scheduled supplier inventory

## Context
Operations currently upload consolidated JSON exports.
`src/feed.py` validates exports and normalizes quantities.
It returns a revision and a quantity map; it does not persist data.
These quantities describe supplier stock for display.
Checkout independently confirms availability with the supplier.

## Goals and requirements
R1: Publish supplier changes within 7 minutes during healthy operation.
This applies to exports of at most 120,000 rows and 16 MiB.
R2: Each API response must reflect one complete supplier revision.
R3: Failed imports must preserve the published quantities.
R4: After 30 minutes without a successful check, return unknown stock.
R5: Credentials must stay out of stored exports and logs.

## Proposed design
Start one import per supplier every 300 seconds.
ADR-002 replaces the hourly cadence in ADR-001.
Acquire a PostgreSQL session advisory lock keyed by supplier.
Use that connection for publication and hold the lock through the run.
Skip a tick if locked; connection loss aborts publication.
Fetch `GET /snapshot` over HTTPS using a secret-store bearer token.
The supplier guarantees the latest committed export at request start.
Set a 60-second download deadline and a 16 MiB body limit.
Log supplier, revision, duration and result; never headers or bodies.
Decode JSON and call `parse_snapshot(doc, supplier)` before writing.
Negative input quantities become zero through the existing parser.
A complete zero-row export publishes an empty inventory.
Begin a transaction and read the supplier's current revision.
Reject lower revisions without advancing the successful-check time.
For an equal revision, retain stock and update only `checked_at`.
For a greater revision, insert its rows and atomically switch the pointer.
Set `checked_at` to request start, when the export was current.
Any download, validation or database failure leaves state unchanged.
Release the lock after completion; retry at the next scheduled tick.
Readers join the pointer and stock in one SQL statement.
An absent pointer or age of at least 30 minutes yields unknown stock.
For a fresh snapshot, an absent SKU has quantity zero.

## Data model and interfaces
Export fields: `supplier`, `revision`, `complete`, `row_count`, `rows`.
Each row contains `sku` and a signed 32-bit integer `quantity`.
SKUs are unique, nonempty strings of at most 64 characters.
Revisions are nonnegative integers, increasing whenever content changes.
The supplier guarantees immutable content for a given revision.
`state(supplier PK, current_revision nullable, checked_at nullable)`.
`snapshot(supplier, revision, row_count)` has a composite primary key.
`stock(supplier, revision, sku, quantity)` keys all three identifiers.
State's pointer and stock rows reference the matching snapshot key.
All tables live in PostgreSQL; quantities stored in stock are nonnegative.
`GET /inventory?supplier=S&sku=A&sku=B` is an authenticated internal API.
Return revision, checked_at, and one result per requested SKU.
Unknown results have `quantity: null`; known results have an integer.
Use one statement for metadata, freshness and all requested quantities.

## Implementation and rollout
Create the schema, publisher, fetch worker and read API.
Add a manual import command using the same lock and publisher.
Only configured suppliers may be fetched or manually imported.
Enforce transport size limits before decoding the response.
Benchmark maximum-size exports against the supplier's test endpoint.
Budgets: download 60 seconds, parse 10, database publication 20.
The 90-second run plus 300-second polling delay is 390 seconds, below 420.
Shadow scheduled imports for seven days without serving their results.
Compare normalized maps against manual parsing of the same exports.
Exercise empty, negative, duplicate-SKU, timeout and connection-loss cases.
Enable API reads for one supplier, then all configured suppliers.
Done means budgets pass and no partial revision is observed under load.
Rollback disables scheduled imports and returns to manual publication.
The API keeps its freshness rule during rollback.
Keep published snapshots and the schema throughout rollback.
Delete unreferenced snapshots older than 48 hours in transactions.
Cleanup excludes the current pointer; statement snapshots protect readers.
