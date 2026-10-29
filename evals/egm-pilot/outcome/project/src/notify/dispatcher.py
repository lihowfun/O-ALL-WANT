"""Single-region dispatcher: one process sends every notification."""

from notify.config import CHANNELS, REGION


class Dispatcher:
    def __init__(self, senders, store):
        self._senders = senders  # channel name -> callable(address, body) -> bool
        self._store = store

    def send(self, notification):
        for address in notification["addresses"]:
            channel = address["channel"]
            if channel not in CHANNELS:
                continue
            delivered = self._senders[channel](address["value"], notification["body"])
            self._store.record(notification["id"], address["value"], channel,
                               "delivered" if delivered else "failed")
        return REGION
