"""Assignment caching and traffic split on serving nodes."""
import logging
import zlib
from dataclasses import dataclass

POLL_INTERVAL_S = 20
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Assignment:
    model: str
    stable_version: str
    canary_version: str | None
    canary_percent: int
    generation: int


def bucket_for(model: str, request_key: str) -> int:
    """Bucket in [0, 100), identical on every node."""
    return zlib.crc32(f"{model}:{request_key}".encode()) % 100


def resolve_version(a: Assignment, request_key: str, pin: str | None) -> str:
    if pin is not None:
        return pin
    if a.canary_version is None or a.canary_percent == 0:
        return a.stable_version
    if bucket_for(a.model, request_key) < a.canary_percent:
        return a.canary_version
    return a.stable_version


def refresh(cache: dict[str, Assignment], client, models) -> None:
    for model in models:
        try:
            fetched = client.fetch_assignment(model)
        except ConnectionError:
            log.warning("registry unreachable; keeping cached %s", model)
            continue
        known = cache.get(model)
        if known is None or fetched.generation > known.generation:
            cache[model] = fetched
