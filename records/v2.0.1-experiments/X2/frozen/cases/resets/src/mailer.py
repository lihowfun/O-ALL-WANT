from dataclasses import dataclass


@dataclass(frozen=True)
class Receipt:
    provider_id: str


class MailUnavailable(RuntimeError):
    pass


def send(provider, outbox_id, recipient, template, values):
    payload = dict(recipient=recipient, template=template, values=values)
    response = provider.submit(payload, idempotency_key=str(outbox_id))
    if response.status != 202:
        raise MailUnavailable(response.status)
    if not response.receipt_id:
        raise MailUnavailable("Acceptance receipt missing")
    return Receipt(response.receipt_id)
