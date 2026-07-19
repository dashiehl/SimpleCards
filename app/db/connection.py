import sqlite3
from contextlib import contextmanager

from app.config import DB_PATH, SCHEMA_PATH


def get_connection(db_path=None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path or DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


_NEW_COLUMNS = {
    "decks": [
        ("front_fields", "TEXT NOT NULL DEFAULT '[\"front\"]'"),
        ("back_fields", "TEXT NOT NULL DEFAULT '[\"back\"]'"),
    ],
    "cards": [
        ("tags", "TEXT NOT NULL DEFAULT '[]'"),
    ],
    "card_review_state": [
        ("lapses", "INTEGER NOT NULL DEFAULT 0"),
    ],
}


def _apply_column_migrations(conn: sqlite3.Connection) -> None:
    for table, columns in _NEW_COLUMNS.items():
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, ddl in columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db(db_path=None) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text())
        _apply_column_migrations(conn)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def db_session(db_path=None):
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
