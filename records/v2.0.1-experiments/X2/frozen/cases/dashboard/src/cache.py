"""Response cache for dashboard chart queries."""

import hashlib
import json

import redis

TTL_SECONDS = 3600


def cache_key(tenant_id: str, schema: str, chart_id: str, params: dict) -> str:
    digest = hashlib.sha256(json.dumps(params, sort_keys=True).encode())
    return f"chart:{tenant_id}:{schema}:{chart_id}:{digest.hexdigest()[:16]}"


class ChartCache:
    def __init__(self, client: redis.Redis):
        self._client = client

    def get(self, key: str):
        raw = self._client.get(key)
        return None if raw is None else json.loads(raw)

    def put(self, key: str, value: dict) -> None:
        self._client.set(key, json.dumps(value, default=str), ex=TTL_SECONDS)
