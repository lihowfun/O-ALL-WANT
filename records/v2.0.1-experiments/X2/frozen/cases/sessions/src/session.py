from dataclasses import dataclass
from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4

ACCESS_SECONDS = 600
REFRESH_SECONDS = 30 * 24 * 60 * 60


@dataclass
class Session:
    id: str
    user_id: str
    refresh_digest: str
    refresh_until: int
    revoked: bool = False


def digest(raw: str) -> str:
    return sha256(raw.encode("utf-8")).hexdigest()


def new_session(user_id: str, now: int) -> tuple[Session, str]:
    raw = token_urlsafe(32)
    session = Session(str(uuid4()), user_id, digest(raw),
                      now + REFRESH_SECONDS)
    return session, raw


def refresh_claims(session: Session, now: int) -> dict:
    if session.revoked or now >= session.refresh_until:
        raise ValueError("invalid_grant")
    return {
        "sub": session.user_id,
        "sid": session.id,
        "iat": now,
        "exp": min(now + ACCESS_SECONDS, session.refresh_until),
    }
