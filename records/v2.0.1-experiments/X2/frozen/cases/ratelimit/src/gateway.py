import hashlib
import threading
import time

_lock = threading.Lock()
_second = 0
_counts = {}


def authenticate(headers, credential_index):
    authorization = headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise PermissionError("credential required")
    digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
    account = credential_index.get(digest)
    if account is None:
        raise PermissionError("invalid credential")
    return account


def handle(headers, path, upstream, credential_index):
    if path == "/healthz":
        return 200, {"status": "ok"}
    account = authenticate(headers, credential_index)
    global _second, _counts
    with _lock:
        second = int(time.time())
        if second != _second:
            _counts = {}
            _second = second
        count = _counts.get(account, 0) + 1
        _counts[account] = count
        if count > 100:
            return 429, {"error": "rate_limit_exceeded"}
    return upstream(account)
