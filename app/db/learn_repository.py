from __future__ import annotations

import sqlite3
import time


def get_progress_map(conn: sqlite3.Connection, deck_id: int) -> dict[int, str]:
    """card_id -> stage ('stage1', 'stage2', 'mastered'). Cards with no row are implicitly 'stage1'."""
    rows = conn.execute(
        "SELECT card_id, stage FROM learn_progress WHERE deck_id = ?", (deck_id,)
    ).fetchall()
    return {row["card_id"]: row["stage"] for row in rows}


def set_stage(conn: sqlite3.Connection, deck_id: int, card_id: int, stage: str) -> None:
    now = int(time.time())
    conn.execute(
        """INSERT INTO learn_progress (card_id, deck_id, stage, updated_at) VALUES (?, ?, ?, ?)
           ON CONFLICT(card_id) DO UPDATE SET stage = excluded.stage, updated_at = excluded.updated_at""",
        (card_id, deck_id, stage, now),
    )


def reset_progress(conn: sqlite3.Connection, deck_id: int) -> None:
    conn.execute("DELETE FROM learn_progress WHERE deck_id = ?", (deck_id,))
