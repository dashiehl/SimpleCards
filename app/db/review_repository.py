from __future__ import annotations

import sqlite3

from app.db.models import CardReviewState
from app.sm2.scheduler import schedule_review


def apply_grade(conn: sqlite3.Connection, card_id: int, grade: int, now: int) -> tuple[CardReviewState, CardReviewState]:
    """Applies a grade and returns (previous_state, new_state) so callers can support undo."""
    row = conn.execute("SELECT * FROM card_review_state WHERE card_id = ?", (card_id,)).fetchone()
    old_state = CardReviewState.from_row(row)
    new_state = schedule_review(old_state, grade, now)

    conn.execute(
        """UPDATE card_review_state
           SET ease_factor = ?, interval_days = ?, repetitions = ?, lapses = ?, due_at = ?, last_reviewed_at = ?
           WHERE card_id = ?""",
        (new_state.ease_factor, new_state.interval_days, new_state.repetitions, new_state.lapses,
         new_state.due_at, new_state.last_reviewed_at, card_id),
    )
    conn.execute(
        """INSERT INTO review_log (card_id, reviewed_at, grade, ease_factor_after, interval_days_after)
           VALUES (?, ?, ?, ?, ?)""",
        (card_id, now, grade, new_state.ease_factor, new_state.interval_days),
    )
    return old_state, new_state


def restore_state(conn: sqlite3.Connection, state: CardReviewState) -> None:
    """Undo support: write a previously-captured state back and drop its most recent log entry."""
    conn.execute(
        """UPDATE card_review_state
           SET ease_factor = ?, interval_days = ?, repetitions = ?, lapses = ?, due_at = ?, last_reviewed_at = ?
           WHERE card_id = ?""",
        (state.ease_factor, state.interval_days, state.repetitions, state.lapses,
         state.due_at, state.last_reviewed_at, state.card_id),
    )
    conn.execute(
        """DELETE FROM review_log WHERE id = (
             SELECT id FROM review_log WHERE card_id = ? ORDER BY reviewed_at DESC, id DESC LIMIT 1
           )""",
        (state.card_id,),
    )


def leech_count(conn: sqlite3.Connection, deck_id: int, threshold: int = 8) -> int:
    row = conn.execute(
        """SELECT COUNT(*) AS n FROM card_review_state crs
           JOIN cards c ON c.id = crs.card_id
           WHERE c.deck_id = ? AND crs.lapses >= ?""",
        (deck_id, threshold),
    ).fetchone()
    return row["n"]


def reviews_since(conn: sqlite3.Connection, deck_id: int, since_epoch: int) -> int:
    row = conn.execute(
        """SELECT COUNT(*) AS n FROM review_log rl
           JOIN cards c ON c.id = rl.card_id
           WHERE c.deck_id = ? AND rl.reviewed_at >= ?""",
        (deck_id, since_epoch),
    ).fetchone()
    return row["n"]


def review_days(conn: sqlite3.Connection, deck_id: int) -> list[int]:
    """Distinct local-midnight epoch days (UTC-based bucketing) that had at least one review, most recent first."""
    rows = conn.execute(
        """SELECT DISTINCT (rl.reviewed_at / 86400) AS day FROM review_log rl
           JOIN cards c ON c.id = rl.card_id
           WHERE c.deck_id = ?
           ORDER BY day DESC""",
        (deck_id,),
    ).fetchall()
    return [row["day"] for row in rows]


def due_forecast(conn: sqlite3.Connection, deck_id: int, now: int, days: int = 7) -> list[int]:
    """Count of cards due on each of the next N days (index 0 = today)."""
    counts = []
    for i in range(days):
        start = now + i * 86400
        end = start + 86400
        row = conn.execute(
            """SELECT COUNT(*) AS n FROM card_review_state crs
               JOIN cards c ON c.id = crs.card_id
               WHERE c.deck_id = ? AND crs.due_at >= ? AND crs.due_at < ?""",
            (deck_id, start, end),
        ).fetchone()
        counts.append(row["n"])
    return counts
