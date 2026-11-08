from threading import RLock

_lock = RLock()
_flags = {
    "new_nav": False,
    "bulk_export": True,
}


def get_global(name: str) -> bool:
    with _lock:
        return _flags.get(name, False)


def set_global(name: str, enabled: bool) -> None:
    if not isinstance(enabled, bool):
        raise TypeError("enabled must be boolean")
    with _lock:
        if name not in _flags:
            raise KeyError(name)
        _flags[name] = enabled


def snapshot() -> dict[str, bool]:
    with _lock:
        return dict(_flags)
