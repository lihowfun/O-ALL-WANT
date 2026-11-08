"""Points ledger: append-only entries in Postgres."""
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg


@dataclass
class Entry:
    member_id: str
    delta: int
    kind: str  # earn, redeem, clawback
    source_ref: str
    created_at: datetime


def append_entry(conn: psycopg.Connection, entry: Entry) -> int:
    with conn.transaction():
        row = conn.execute(
            "INSERT INTO ledger_entries"
            " (member_id, delta, kind, source_ref, created_at)"
            " VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (entry.member_id, entry.delta, entry.kind,
             entry.source_ref, entry.created_at),
        ).fetchone()
    return row[0]


def get_balance(conn: psycopg.Connection, member_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(delta), 0) FROM ledger_entries"
        " WHERE member_id = %s",
        (member_id,),
    ).fetchone()
    return row[0]


def earn_for_order(conn: psycopg.Connection, member_id: str,
                   order_id: str, amount_cents: int) -> int:
    points = amount_cents // 100
    return append_entry(conn, Entry(
        member_id=member_id, delta=points, kind="earn",
        source_ref=f"order:{order_id}",
        created_at=datetime.now(timezone.utc),
    ))
