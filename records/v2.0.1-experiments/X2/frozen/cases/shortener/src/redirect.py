from datetime import datetime, timezone

from db import conn


def resolve(code):
    row = conn.execute(
        "SELECT target_url FROM links WHERE code = ? AND deleted_at IS NULL",
        (code,),
    ).fetchone()
    return row[0] if row else None


def record_click(code):
    day = datetime.now(timezone.utc).date().isoformat()
    conn.execute(
        "INSERT INTO daily_clicks (code, day, clicks) VALUES (?, ?, 1) "
        "ON CONFLICT (code, day) DO UPDATE SET clicks = daily_clicks.clicks + 1",
        (code, day),
    )
    conn.commit()


def handle_redirect(code):
    target = resolve(code)
    if target is None:
        return 404, {}
    record_click(code)
    return 302, {"Location": target}


def link_stats(code, user_id):
    row = conn.execute(
        "SELECT owner_id FROM links WHERE code = ?", (code,)
    ).fetchone()
    if row is None or row[0] != user_id:
        return 404, {}
    days = conn.execute(
        "SELECT day, clicks FROM daily_clicks WHERE code = ? ORDER BY day",
        (code,),
    ).fetchall()
    return 200, {"daily": [{"day": d, "clicks": c} for d, c in days]}
