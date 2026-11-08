from dataclasses import dataclass


@dataclass(frozen=True)
class Session:
    user_id: int
    password_version: int


def session_valid(db, session):
    row = db.execute(
        "SELECT password_version FROM accounts WHERE id = %s",
        (session.user_id,),
    ).fetchone()
    return row is not None and row[0] == session.password_version


def update_password(db, user_id, encoded_hash):
    """Caller holds the account lock and owns the transaction."""
    row = db.execute(
        "UPDATE accounts SET password_hash = %s, "
        "password_version = password_version + 1 WHERE id = %s "
        "RETURNING password_version",
        (encoded_hash, user_id),
    ).fetchone()
    if row is None:
        raise LookupError(user_id)
    return row[0]
