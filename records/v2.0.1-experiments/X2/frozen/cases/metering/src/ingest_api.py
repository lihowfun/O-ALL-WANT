import json
import time

from metering.auth import lookup_api_key
from metering.kafka import producer

TOPIC = "usage-events"
REQUIRED_FIELDS = ("event_id", "tenant_id", "meter", "quantity", "timestamp")


def authenticate(headers):
    key = headers.get("X-Api-Key")
    if not key:
        return None
    record = lookup_api_key(key)
    if record is None or record.revoked:
        return None
    return record


def handle_ingest(headers, body):
    if authenticate(headers) is None:
        return 401, {"error": "unauthorized"}

    try:
        events = json.loads(body)["events"]
    except (ValueError, KeyError):
        return 400, {"error": "malformed body"}

    accepted = 0
    for event in events:
        if any(f not in event for f in REQUIRED_FIELDS):
            continue
        if event["quantity"] < 0:
            continue
        event["received_at"] = time.time()
        producer.send(TOPIC, key=event["tenant_id"], value=event)
        accepted += 1

    producer.flush()
    return 202, {"accepted": accepted}
