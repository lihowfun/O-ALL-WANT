import time
import uuid

import requests

INGEST_URL = "https://metering.internal/v1/events"
BATCH_SIZE = 500
MAX_RETRY_AGE_S = 24 * 3600


class MeterClient:
    def __init__(self, api_key, tenant_id, spool):
        self.api_key = api_key
        self.tenant_id = tenant_id
        self.spool = spool

    def record(self, meter, quantity):
        self.spool.append({
            "event_id": str(uuid.uuid4()),
            "tenant_id": self.tenant_id,
            "meter": meter,
            "quantity": quantity,
            "timestamp": time.time(),
        })

    def flush(self):
        batch = self.spool.peek(BATCH_SIZE)
        if not batch:
            return
        try:
            resp = requests.post(
                INGEST_URL,
                json={"events": batch},
                headers={"X-Api-Key": self.api_key},
                timeout=5,
            )
            ok = resp.status_code == 202
        except requests.RequestException:
            ok = False
        if ok:
            self.spool.remove(batch)
        else:
            self._expire(batch)

    def _expire(self, batch):
        cutoff = time.time() - MAX_RETRY_AGE_S
        self.spool.remove([e for e in batch if e["timestamp"] < cutoff])
