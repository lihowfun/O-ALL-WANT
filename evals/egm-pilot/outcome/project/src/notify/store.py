"""Delivery records, stored in PostgreSQL."""

from datetime import datetime, timezone

from notify.config import DELIVERY_RECORD_RETENTION_DAYS


class DeliveryStore:
    """Writes one row per send attempt. `connect` returns a DB-API connection."""

    def __init__(self, connect):
        self._connect = connect

    def record(self, notification_id, address, channel, outcome):
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO delivery_record (notification_id, address, channel, outcome, sent_at)"
                " VALUES (%s, %s, %s, %s, %s)",
                (notification_id, address, channel, outcome, datetime.now(timezone.utc)),
            )

    def purge_expired(self):
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM delivery_record WHERE sent_at < now() - make_interval(days => %s)",
                (DELIVERY_RECORD_RETENTION_DAYS,),
            )
