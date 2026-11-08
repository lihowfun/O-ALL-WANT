import hashlib
import pathlib

import psycopg

LOCK_KEY = 72_340_001
NO_TX_MARKER = "-- runner: no-transaction"


def record(conn, version: str, sql: str) -> None:
    conn.execute(
        "INSERT INTO schema_migrations (version, checksum, applied_at) VALUES (%s, %s, now())",
        (version, hashlib.sha256(sql.encode()).hexdigest()),
    )


def drop_invalid_index(conn, sql: str) -> None:
    name = sql.split("IF NOT EXISTS", 1)[1].split()[0]
    invalid = conn.execute(
        "SELECT 1 FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid"
        " WHERE c.relname = %s AND NOT i.indisvalid",
        (name,),
    ).fetchone()
    if invalid:
        conn.execute(f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"')


def apply(dsn: str, directory: str) -> None:
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (LOCK_KEY,))
        try:
            done = {v for (v,) in conn.execute("SELECT version FROM schema_migrations")}
            for path in sorted(pathlib.Path(directory).glob("*.sql")):
                version, sql = path.stem, path.read_text()
                if version in done:
                    continue
                if sql.startswith(NO_TX_MARKER):
                    drop_invalid_index(conn, sql)
                    conn.execute(sql)
                    record(conn, version, sql)
                else:
                    with conn.transaction():
                        conn.execute(sql)
                        record(conn, version, sql)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))
