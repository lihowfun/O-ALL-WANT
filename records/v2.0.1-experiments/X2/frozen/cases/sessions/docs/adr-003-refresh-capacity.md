# ADR-003: Refresh capacity
Status: Accepted.
## Context
Tests include rotation, encryption, replays and revocation reads.
Each of four shards sustained 800 refresh requests/s at p99 <250 ms.
## Decision
Use at most 70% of tested throughput per shard.
Route by session ID and colocate replay rows.
Enforce admission at 560 refresh requests/s per shard.
## Consequences
Capacity is 2,240 requests/s; excess receives HTTP 503.
