from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Outcome:
    ok: bool
    payload: Any = None
    error: str | None = None


def invoke(handler: Callable, args: dict, run_id: str) -> Outcome:
    try:
        payload = handler(args, idempotency_key=run_id)
    except Exception as exc:
        return Outcome(ok=False, error=type(exc).__name__)
    return Outcome(ok=True, payload=payload)


def load_run(db, tenant_id: str, run_id: int) -> dict:
    row = db.execute(
        "SELECT id, tenant_id, state, output FROM runs "
        "WHERE id = %s AND tenant_id = %s",
        (run_id, tenant_id),
    ).fetchone()
    if row is None:
        raise LookupError(run_id)
    return dict(row)


def run_inline(db, handler, args, tenant_id, run_id):
    outcome = invoke(handler, args, str(run_id))
    db.execute(
        "UPDATE runs SET state = %s, output = %s, error = %s "
        "WHERE id = %s AND tenant_id = %s",
        ("succeeded" if outcome.ok else "failed",
         outcome.payload, outcome.error, run_id, tenant_id),
    )
    db.commit()
    return load_run(db, tenant_id, run_id)
