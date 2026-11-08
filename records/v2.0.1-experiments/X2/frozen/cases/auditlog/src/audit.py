from datetime import datetime, timezone
from dataclasses import dataclass

SCHEMA = """
CREATE TABLE audit_events (
  tenant_id text NOT NULL, event_id text NOT NULL,
  event_day date NOT NULL, action text NOT NULL,
  PRIMARY KEY (tenant_id, event_id)
);
"""

@dataclass(frozen=True)
class Principal:
    tenant_id: str
    role: str


def ingest(db, tenant_id, event_id, action):
    day = datetime.now(timezone.utc).date()
    with db.transaction():
        db.execute(
            "INSERT INTO audit_events VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,event_id) DO NOTHING",
            (tenant_id, event_id, day, action),
        )


def query(db, principal, tenant_id, day):
    if principal.role != "auditor" or principal.tenant_id != tenant_id:
        raise PermissionError("tenant access denied")
    return db.execute(
        "SELECT event_id,action FROM audit_events "
        "WHERE tenant_id=%s AND event_day=%s ORDER BY event_id",
        (tenant_id, day),
    ).fetchall()
