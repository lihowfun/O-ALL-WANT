"""Relays change_log rows to Kafka topics cdc.<table>."""

import json
import time

BATCH_SIZE = 500
POLL_INTERVAL_S = 1.0
PUBLISHED_OPS = {"INSERT": "c", "UPDATE": "u"}


def fetch_batch(conn, after_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, table_name, op, pk, row_data, committed_at"
        " FROM change_log WHERE id > %s ORDER BY id LIMIT %s",
        (after_id, BATCH_SIZE),
    )
    return cur.fetchall()


def publish_change(producer, row):
    change_id, table, op, pk, row_data, committed_at = row
    if op not in PUBLISHED_OPS:
        return
    event = {"change_id": change_id, "table": table, "op": PUBLISHED_OPS[op],
             "pk": pk, "after": row_data, "ts": committed_at.isoformat()}
    producer.send(f"cdc.{table}", key=str(pk), value=json.dumps(event))


def run(conn, producer, cursor_store):
    last_id = cursor_store.load()
    while True:
        rows = fetch_batch(conn, last_id)
        for row in rows:
            publish_change(producer, row)
        if rows:
            producer.flush()
            last_id = rows[-1][0]
            cursor_store.save(last_id)
        else:
            time.sleep(POLL_INTERVAL_S)
