from __future__ import annotations

import json
import sqlite3
import time

from app.db.models import Card, CardReviewState


def create_card(
    conn: sqlite3.Connection,
    deck_id: int,
    front: str,
    back: str | None = None,
    kind: str = "basic",
    extra_fields: dict | None = None,
    tags: list[str] | None = None,
    source_ref: str | None = None,
) -> Card:
    now = int(time.time())
    extra_fields = extra_fields or {}
    tags = tags or []
    cur = conn.execute(
        """INSERT INTO cards (deck_id, kind, front, back, extra_fields, tags, source_ref, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (deck_id, kind, front, back, json.dumps(extra_fields), json.dumps(tags), source_ref, now, now),
    )
    card_id = cur.lastrowid
    conn.execute(
        "INSERT INTO card_review_state (card_id, due_at) VALUES (?, ?)",
        (card_id, now),
    )
    return Card(
        id=card_id, deck_id=deck_id, kind=kind, front=front, back=back,
        extra_fields=extra_fields, tags=tags, source_ref=source_ref, created_at=now, updated_at=now,
    )


def list_cards(conn: sqlite3.Connection, deck_id: int) -> list[Card]:
    rows = conn.execute("SELECT * FROM cards WHERE deck_id = ? ORDER BY created_at", (deck_id,)).fetchall()
    return [Card.from_row(row) for row in rows]


def search_cards(conn: sqlite3.Connection, deck_id: int, query: str = "", tag: str | None = None) -> list[Card]:
    rows = conn.execute("SELECT * FROM cards WHERE deck_id = ? ORDER BY created_at", (deck_id,)).fetchall()
    cards = [Card.from_row(row) for row in rows]
    if query:
        q = query.lower()
        cards = [c for c in cards if q in c.front.lower() or q in (c.back or "").lower()
                 or any(q in v.lower() for v in c.extra_fields.values() if isinstance(v, str))]
    if tag:
        cards = [c for c in cards if tag in c.tags]
    return cards


def all_tags(conn: sqlite3.Connection, deck_id: int) -> list[str]:
    rows = conn.execute("SELECT tags FROM cards WHERE deck_id = ?", (deck_id,)).fetchall()
    tags: set[str] = set()
    for row in rows:
        tags.update(json.loads(row["tags"] or "[]"))
    return sorted(tags)


def get_card(conn: sqlite3.Connection, card_id: int) -> Card | None:
    row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    return Card.from_row(row) if row else None


def update_card(conn: sqlite3.Connection, card: Card) -> None:
    conn.execute(
        """UPDATE cards SET kind = ?, front = ?, back = ?, extra_fields = ?, tags = ?, source_ref = ?, updated_at = ?
           WHERE id = ?""",
        (card.kind, card.front, card.back, json.dumps(card.extra_fields), json.dumps(card.tags),
         card.source_ref, int(time.time()), card.id),
    )


def delete_card(conn: sqlite3.Connection, card_id: int) -> None:
    conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))


def get_due_cards(conn: sqlite3.Connection, deck_id: int, now: int | None = None) -> list[Card]:
    now = now if now is not None else int(time.time())
    rows = conn.execute(
        """SELECT c.* FROM cards c
           JOIN card_review_state crs ON crs.card_id = c.id
           WHERE c.deck_id = ? AND crs.due_at <= ?
           ORDER BY crs.due_at ASC""",
        (deck_id, now),
    ).fetchall()
    return [Card.from_row(row) for row in rows]


def get_review_state(conn: sqlite3.Connection, card_id: int) -> CardReviewState | None:
    row = conn.execute("SELECT * FROM card_review_state WHERE card_id = ?", (card_id,)).fetchone()
    return CardReviewState.from_row(row) if row else None


def field_keys_in_use(conn: sqlite3.Connection, deck_id: int) -> list[str]:
    """All field keys available for this deck's cards: 'front', 'back', plus any extra_fields keys."""
    rows = conn.execute("SELECT extra_fields FROM cards WHERE deck_id = ?", (deck_id,)).fetchall()
    keys = {"front", "back"}
    for row in rows:
        keys.update(json.loads(row["extra_fields"] or "{}").keys())
    return sorted(keys)
