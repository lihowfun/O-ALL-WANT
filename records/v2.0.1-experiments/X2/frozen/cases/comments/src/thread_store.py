from psycopg import Connection


class Forbidden(Exception):
    pass


def require_document_read(
    conn: Connection, user_id: str, document_id: str
) -> None:
    row = conn.execute(
        "SELECT 1 FROM document_members "
        "WHERE document_id = %s AND user_id = %s",
        (document_id, user_id),
    ).fetchone()
    if row is None:
        raise Forbidden(document_id)


def list_threads(
    conn: Connection, user_id: str, document_id: str
) -> list[tuple]:
    require_document_read(conn, user_id, document_id)
    return conn.execute(
        "SELECT id, document_id, body, status, created_at FROM threads "
        "WHERE document_id = %s AND status = 'open' "
        "ORDER BY created_at, id",
        (document_id,),
    ).fetchall()
