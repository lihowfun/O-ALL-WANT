from html import escape


def pending_for_user(db, user_id, through):
    return db.execute(
        """SELECT id, body FROM notifications
           WHERE user_id = ? AND emailed_at IS NULL AND created_at <= ?
           ORDER BY created_at, id LIMIT 100""",
        (user_id, through),
    ).fetchall()


def render_digest(user, events):
    items = "".join(f"<li>{escape(event['body'])}</li>" for event in events)
    return f"<h1>Hello {escape(user['name'])}</h1><ul>{items}</ul>"


def dispatch(provider, key, address, body):
    result = provider.put_message(
        key=key,
        address=address,
        html=body,
    )
    if result["accepted"]:
        return result["id"]
    raise RuntimeError("Provider rejected message")
