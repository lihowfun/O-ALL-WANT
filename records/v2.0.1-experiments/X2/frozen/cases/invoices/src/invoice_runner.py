from billing import db, mailer, payments, pdf, tax
from proration import plan_change_lines

MIN_CHARGE_CENTS = 50


def run_month(period_start, period_end):
    for sub in db.active_subscriptions(period_start):
        invoice = build_invoice(sub, period_start, period_end)
        finalize_and_charge(invoice, sub)


def build_invoice(sub, period_start, period_end):
    invoice = db.create_draft_invoice(sub.id, period_start)
    lines = [("plan", sub.plan_price_cents)]
    if sub.plan_change:
        ch = sub.plan_change
        lines += plan_change_lines(ch.old_cents, ch.new_cents, ch.day, ch.period_days)
    lines += [("usage", u.amount_cents) for u in db.usage_for(sub.id, period_start)]
    balance = db.take_carried_balance_cents(sub.id)
    if balance:
        lines.append(("carried balance", balance))
    lines.append(("tax", tax.quote(sub.billing_address, lines)))
    db.set_lines(invoice.id, lines)
    return db.get_invoice(invoice.id)


def finalize_and_charge(invoice, sub):
    invoice = db.finalize(invoice.id)  # assigns the yearly sequential number
    if invoice.total_cents < MIN_CHARGE_CENTS:
        db.carry_balance(sub.id, invoice.total_cents)
        return
    result = payments.charge(sub.customer_id, invoice.total_cents,
                             idempotency_key=f"invoice:{invoice.id}")
    db.mark(invoice.id, "paid" if result.ok else "failed")
    url = pdf.render_and_upload(invoice)
    mailer.send_invoice(sub.customer_email, invoice.number, url)
