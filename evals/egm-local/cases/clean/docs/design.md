# Customer lookup cache

## Scope and goals
Apply ADR-012 to the lookup service. Redis is a disposable cache, and PostgreSQL remains authoritative. Customer display names are public application data. No tokens or private profile fields enter this cache.

## Terms and flow
A cache miss means the customer_id has no Redis entry. A cache worker reads currently committed public display names from PostgreSQL, not old event bodies. Cache writes reject older database versions; expiry is based on the database-read timestamp and is never extended past 60 seconds by a delayed write. Reads use Redis if present, otherwise PostgreSQL; the database fallback is provisioned for full traffic during total cache loss. The cache adapter reports every connection/service failure as CacheUnavailable; lookup catches it and falls back. Entries expire after 60 s; a name may be stale for at most that interval under the declared eventual consistency contract.

## Retention
Hot request diagnostics retain 7 days. A separate immutable archive retains 90 days. Support's 30-day lookups query that archive; expiry in the hot store does not delete archive objects. Diagnostics contain request IDs and timing, not request headers or personal fields.

## Acceptance and rollout
Under 1,000 lookups/s: p99 below 80 ms with warm cache and below 200 ms during a full cache outage. Tests cover misses, expiry, current name visibility after 60 s, cache outage and the archive path for a 30-day-old request. Roll out to 5%, then 25%, then 100% after each 24-hour error-budget check. Rollback disables cache reads and uses the already provisioned PostgreSQL fallback. These are release acceptance criteria, not a claim that tests already passed.
