import sqlite3


def create_delivery(db, tenant_id, endpoint_id, event_id, body):
    with db:
        endpoint = db.execute(
            "SELECT id FROM endpoints WHERE id = ? AND tenant_id = ?",
            (endpoint_id, tenant_id),
        ).fetchone()
        if endpoint is None:
            raise LookupError("endpoint")
        db.execute(
            "INSERT INTO deliveries "
            "(tenant_id, endpoint_id, event_id, body, state) "
            "VALUES (?, ?, ?, ?, 'PENDING') "
            "ON CONFLICT(tenant_id, endpoint_id, event_id) DO NOTHING",
            (tenant_id, endpoint_id, event_id, body),
        )
        return db.execute(
            "SELECT id FROM deliveries "
            "WHERE tenant_id = ? AND endpoint_id = ? AND event_id = ?",
            (tenant_id, endpoint_id, event_id),
        ).fetchone()[0]


def get_delivery(db: sqlite3.Connection, tenant_id, delivery_id):
    return db.execute(
        "SELECT id, event_id, body, state FROM deliveries "
        "WHERE tenant_id = ? AND id = ?",
        (tenant_id, delivery_id),
    ).fetchone()
