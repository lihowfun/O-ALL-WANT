from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal


def days_in_period(start: date, end: date) -> int:
    return (end - start).days


def prorate_cents(price_cents: int, used_days: int, period_days: int) -> int:
    """Share of a period price for the days used, rounded half-even to cents."""
    if period_days <= 0:
        raise ValueError("period_days must be positive")
    share = Decimal(price_cents) * used_days / period_days
    return int(share.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def plan_change_lines(old_cents: int, new_cents: int, change_day: int,
                      period_days: int) -> list[tuple[str, int]]:
    """Credit the unused part of the old plan, charge the new plan for it."""
    remaining = period_days - change_day
    return [
        ("plan credit", -prorate_cents(old_cents, remaining, period_days)),
        ("plan charge", prorate_cents(new_cents, remaining, period_days)),
    ]
