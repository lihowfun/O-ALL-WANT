"""Seller ledger: one row per order, written by the order service."""

from dataclasses import dataclass

from db import conn


@dataclass
class LedgerEntry:
    entry_id: int
    seller_id: int
    order_id: int
    amount_cents: int    # seller share after commission
    refunded_cents: int
    status: str          # open | settled | paid_out


def record_sale(seller_id: int, order_id: int, amount_cents: int) -> int:
    row = conn.execute(
        "INSERT INTO ledger_entries (seller_id, order_id, amount_cents,"
        " refunded_cents, status) VALUES (%s, %s, %s, 0, 'open')"
        " RETURNING entry_id",
        (seller_id, order_id, amount_cents),
    ).fetchone()
    return row[0]


def record_refund(order_id: int, refund_cents: int) -> None:
    conn.execute(
        "UPDATE ledger_entries SET refunded_cents = refunded_cents + %s"
        " WHERE order_id = %s",
        (refund_cents, order_id),
    )


def settle(order_id: int) -> None:
    """Called by fulfilment once the order is delivered."""
    conn.execute(
        "UPDATE ledger_entries SET status = 'settled' WHERE order_id = %s",
        (order_id,),
    )


def seller_balance_cents(seller_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_cents - refunded_cents), 0)"
        " FROM ledger_entries WHERE seller_id = %s AND status = 'settled'",
        (seller_id,),
    ).fetchone()
    return row[0]
