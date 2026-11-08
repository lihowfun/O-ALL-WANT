# ADR-002: Handler effect receipts
Status: Accepted

## Decision
Delivery is at least once, including after lease expiry.
Every handler receives the stable run ID as its idempotency key.
The effect service atomically commits the effect and a receipt for that key.
Repeated calls return the committed result without repeating the effect.
Failure before commit leaves the key eligible for retry.

## Consequences
Handlers without this contract cannot enter the registry.
Keep the run ID across retries and lease recovery.
