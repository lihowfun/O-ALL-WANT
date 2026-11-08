from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class Coupon:
    code: str
    percent: int
    min_subtotal_cents: int
    expires_at: datetime


def discount_cents(subtotal_cents: int, coupon: Coupon | None) -> int:
    if coupon is None:
        return 0
    if subtotal_cents < coupon.min_subtotal_cents:
        raise ValueError("minimum spend")
    amount = Decimal(subtotal_cents) * coupon.percent / 100
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def tax_cents(net_cents: int, rate: Decimal) -> int:
    return int((net_cents * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def internal_quote(line_nets: list[int], rate: Decimal, shipping_cents: int) -> dict:
    subtotal = sum(line_nets)
    tax = sum(tax_cents(net, rate) for net in line_nets)
    return {
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping_cents,
        "total": subtotal + tax + shipping_cents,
    }
