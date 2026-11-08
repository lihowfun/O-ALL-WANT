"""Reads dashboard rows from the published nightly snapshot."""

import psycopg
from psycopg import sql

POINTER_SQL = "SELECT schema_name, taken_at FROM snapshot_pointer WHERE id = 1"


class SnapshotReader:
    def __init__(self, dsn: str):
        self._dsn = dsn

    def run(self, tenant_id: str, query: str, params: dict) -> dict:
        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(POINTER_SQL).fetchone()
            if row is None:
                raise LookupError("no snapshot published")
            schema, taken_at = row
            conn.execute(
                sql.SQL("SET LOCAL search_path TO {}").format(
                    sql.Identifier(schema)
                )
            )
            rows = conn.execute(
                query, {**params, "tenant_id": tenant_id}
            ).fetchall()
        return {"schema": schema, "taken_at": taken_at, "rows": rows}
