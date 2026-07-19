from __future__ import annotations

import json
import sqlite3
import time

from app.db.models import DEFAULT_BACK_FIELDS, DEFAULT_FRONT_FIELDS, Deck


def create_deck(
    conn: sqlite3.Connection,
    name: str,
    description: str = "",
    source: str = "manual",
    front_fields: list[str] | None = None,
    back_fields: list[str] | None = None,
) -> Deck:
    now = int(time.time())
    front_fields = front_fields or list(DEFAULT_FRONT_FIELDS)
    back_fields = back_fields or list(DEFAULT_BACK_FIELDS)
    cur = conn.execute(
        """INSERT INTO decks (name, description, source, front_fields, back_fields, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, description, source, json.dumps(front_fields), json.dumps(back_fields), now, now),
    )
    return Deck(
        id=cur.lastrowid, name=name, description=description, source=source,
        front_fields=front_fields, back_fields=back_fields, created_at=now, updated_at=now,
    )


def list_decks(conn: sqlite3.Connection) -> list[Deck]:
    now = int(time.time())
    rows = conn.execute("SELECT * FROM decks ORDER BY name").fetchall()
    decks = []
    for row in rows:
        deck = Deck.from_row(row)
        counts = conn.execute(
            """SELECT
                 COUNT(*) AS total,
                 SUM(CASE WHEN crs.due_at <= ? THEN 1 ELSE 0 END) AS due
               FROM cards c
               LEFT JOIN card_review_state crs ON crs.card_id = c.id
               WHERE c.deck_id = ?""",
            (now, deck.id),
        ).fetchone()
        deck.total_count = counts["total"] or 0
        deck.due_count = counts["due"] or 0
        decks.append(deck)
    return decks


def get_deck(conn: sqlite3.Connection, deck_id: int) -> Deck | None:
    row = conn.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)).fetchone()
    return Deck.from_row(row) if row else None


def delete_deck(conn: sqlite3.Connection, deck_id: int) -> None:
    conn.execute("DELETE FROM decks WHERE id = ?", (deck_id,))


def rename_deck(conn: sqlite3.Connection, deck_id: int, name: str) -> None:
    conn.execute("UPDATE decks SET name = ?, updated_at = ? WHERE id = ?", (name, int(time.time()), deck_id))


def set_field_layout(conn: sqlite3.Connection, deck_id: int, front_fields: list[str], back_fields: list[str]) -> None:
    conn.execute(
        "UPDATE decks SET front_fields = ?, back_fields = ?, updated_at = ? WHERE id = ?",
        (json.dumps(front_fields), json.dumps(back_fields), int(time.time()), deck_id),
    )
