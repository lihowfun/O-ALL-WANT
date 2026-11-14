# ADR-001: inventory state
Status: accepted; revision r2; date 2026-09-10.
Inventory quantities and reservations use PostgreSQL. A second persistent inventory database needs an accepted replacement ADR before implementation. Client retries must not reserve stock twice: reserve(order_id, sku, quantity) is idempotent per order_id.
