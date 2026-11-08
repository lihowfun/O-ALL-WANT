"""Legacy privacy export helpers used by the support console."""
import json
from datetime import datetime, timedelta, timezone

LEGAL_DEADLINE_DAYS = 30


def open_task(db, session, note=""):
    """Record an export request for the signed-in customer."""
    now = datetime.now(timezone.utc)
    return db.insert(
        "export_tasks",
        user_id=session.user_id,
        status="open",
        note=note,
        created_at=now,
        due_at=now + timedelta(days=LEGAL_DEADLINE_DAYS),
    )


def collect_profile(db, user_id):
    row = db.one("SELECT * FROM users WHERE id = %s", user_id)
    row.pop("password_hash", None)
    return row


def collect_orders(db, user_id):
    return db.all("SELECT * FROM orders WHERE user_id = %s", user_id)


def collect_addresses(db, user_id):
    return db.all("SELECT * FROM addresses WHERE user_id = %s", user_id)


COLLECTORS = {
    "profile": collect_profile,
    "orders": collect_orders,
    "addresses": collect_addresses,
}


def build_export(db, user_id):
    """Run every collector and return the archive body as JSON bytes."""
    payload = {name: fn(db, user_id) for name, fn in COLLECTORS.items()}
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    return json.dumps(payload, default=str).encode()


def close_task(db, task_id):
    db.update("export_tasks", task_id, status="done")
