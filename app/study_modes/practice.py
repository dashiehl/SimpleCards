from __future__ import annotations

import difflib
import random
import re

from app.db.models import Card

_PUNCT_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def prompt_text(card: Card, field_keys: list[str]) -> str:
    """Plain-text join of the given fields on a card, skipping empties."""
    parts = [card.field_value(key) for key in field_keys]
    return "\n".join(p for p in parts if p)


def pick_distractors(cards: list[Card], correct_card: Card, field_keys: list[str], count: int) -> list[str]:
    """Up to `count` unique, non-empty prompt texts drawn from cards other than `correct_card`."""
    correct_text = prompt_text(correct_card, field_keys)
    pool = []
    seen = {correct_text}
    for c in cards:
        if c.id == correct_card.id:
            continue
        text = prompt_text(c, field_keys)
        if text and text not in seen:
            pool.append(text)
            seen.add(text)
    random.shuffle(pool)
    return pool[:count]


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = _PUNCT_RE.sub("", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def fuzzy_match(user_text: str, correct_text: str, threshold: float = 0.82) -> bool:
    """True if `user_text` is an exact or close-enough match to `correct_text`,
    tolerating minor spelling/punctuation/whitespace variation."""
    a, b = _normalize(user_text), _normalize(correct_text)
    if not a or not b:
        return False
    if a == b:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= threshold
