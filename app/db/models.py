from __future__ import annotations

import json
from dataclasses import dataclass, field

DEFAULT_FRONT_FIELDS = ["front"]
DEFAULT_BACK_FIELDS = ["back"]

LEECH_THRESHOLD = 8


@dataclass
class Deck:
    id: int | None
    name: str
    description: str = ""
    source: str = "manual"
    front_fields: list[str] = field(default_factory=lambda: list(DEFAULT_FRONT_FIELDS))
    back_fields: list[str] = field(default_factory=lambda: list(DEFAULT_BACK_FIELDS))
    created_at: int = 0
    updated_at: int = 0
    due_count: int = 0
    total_count: int = 0

    @classmethod
    def from_row(cls, row) -> "Deck":
        return cls(
            id=row["id"], name=row["name"], description=row["description"],
            source=row["source"],
            front_fields=json.loads(row["front_fields"] or "[\"front\"]"),
            back_fields=json.loads(row["back_fields"] or "[\"back\"]"),
            created_at=row["created_at"], updated_at=row["updated_at"],
        )


@dataclass
class Card:
    id: int | None
    deck_id: int
    kind: str = "basic"
    front: str = ""
    back: str | None = None
    extra_fields: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    source_ref: str | None = None
    created_at: int = 0
    updated_at: int = 0

    def field_value(self, key: str) -> str:
        if key == "front":
            return self.front or ""
        if key == "back":
            return self.back or ""
        return self.extra_fields.get(key, "")

    @classmethod
    def from_row(cls, row) -> "Card":
        return cls(
            id=row["id"], deck_id=row["deck_id"], kind=row["kind"], front=row["front"],
            back=row["back"], extra_fields=json.loads(row["extra_fields"] or "{}"),
            tags=json.loads(row["tags"] or "[]"),
            source_ref=row["source_ref"], created_at=row["created_at"], updated_at=row["updated_at"],
        )


@dataclass
class CardReviewState:
    card_id: int
    ease_factor: float = 2.5
    interval_days: int = 0
    repetitions: int = 0
    lapses: int = 0
    due_at: int = 0
    last_reviewed_at: int | None = None

    @property
    def is_leech(self) -> bool:
        return self.lapses >= LEECH_THRESHOLD

    @classmethod
    def from_row(cls, row) -> "CardReviewState":
        return cls(
            card_id=row["card_id"], ease_factor=row["ease_factor"],
            interval_days=row["interval_days"], repetitions=row["repetitions"],
            lapses=row["lapses"], due_at=row["due_at"], last_reviewed_at=row["last_reviewed_at"],
        )


@dataclass
class SessionHistoryEntry:
    id: int
    deck_id: int
    mode: str
    summary: str
    completed_at: int

    @classmethod
    def from_row(cls, row) -> "SessionHistoryEntry":
        return cls(
            id=row["id"], deck_id=row["deck_id"], mode=row["mode"],
            summary=row["summary"], completed_at=row["completed_at"],
        )
