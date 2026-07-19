from __future__ import annotations

import sqlite3
import time

from app.db.models import SessionHistoryEntry

VALID_MODES = ("flashcards", "match", "learn", "test")


def log_session(conn: sqlite3.Connection, deck_id: int, mode: str, summary: str) -> None:
    if mode not in VALID_MODES:
        raise ValueError(f"Unknown session mode: {mode!r}")
    conn.execute(
        "INSERT INTO session_history (deck_id, mode, summary, completed_at) VALUES (?, ?, ?, ?)",
        (deck_id, mode, summary, int(time.time())),
    )


def list_history(conn: sqlite3.Connection, deck_id: int, limit: int = 100) -> list[SessionHistoryEntry]:
    rows = conn.execute(
        """SELECT * FROM session_history WHERE deck_id = ?
           ORDER BY completed_at DESC LIMIT ?""",
        (deck_id, limit),
    ).fetchall()
    return [SessionHistoryEntry.from_row(row) for row in rows]
