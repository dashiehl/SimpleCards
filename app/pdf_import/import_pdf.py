from __future__ import annotations

import sqlite3

from app.db import card_repository, deck_repository
from app.db.field_layout import suggest_layout
from app.pdf_import.candidate import CandidateCard
from app.pdf_import.extractor import extract_spans
from app.pdf_import.splitter import split_into_candidates


def extract_candidates(pdf_path: str, mode: str = "auto") -> list[CandidateCard]:
    spans = extract_spans(pdf_path)
    return split_into_candidates(spans, mode=mode)


def commit_candidates_to_new_deck(conn: sqlite3.Connection, deck_name: str, candidates: list[CandidateCard],
                                   description: str = "", front_fields: list[str] | None = None,
                                   back_fields: list[str] | None = None) -> int:
    deck = deck_repository.create_deck(conn, deck_name, description=description, source="pdf_import")
    commit_candidates_to_deck(conn, deck.id, candidates, front_fields=front_fields, back_fields=back_fields)
    return deck.id


def commit_candidates_to_deck(conn: sqlite3.Connection, deck_id: int, candidates: list[CandidateCard],
                               front_fields: list[str] | None = None, back_fields: list[str] | None = None) -> int:
    included = [c for c in candidates if c.include]
    for c in included:
        card_repository.create_card(
            conn, deck_id=deck_id, front=c.front, back=c.back, kind=c.kind,
            extra_fields=c.extra_fields, source_ref=c.source_ref,
        )

    if front_fields is None or back_fields is None:
        available = card_repository.field_keys_in_use(conn, deck_id)
        front_fields, back_fields = suggest_layout(available)
    deck_repository.set_field_layout(conn, deck_id, front_fields, back_fields)
    return len(included)
