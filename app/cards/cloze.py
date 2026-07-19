from __future__ import annotations

import re

CLOZE_RE = re.compile(r"\{\{c\d+::(.*?)(?:::.*?)?\}\}")


def has_cloze_markers(text: str) -> bool:
    return bool(CLOZE_RE.search(text or ""))


def masked_text(text: str) -> str:
    """Replace each cloze answer with a blank, for the question side."""
    return CLOZE_RE.sub("[...]", text or "")


def revealed_text(text: str) -> str:
    """Strip cloze markup down to the plain answer text, for the answer side."""
    return CLOZE_RE.sub(lambda m: m.group(1), text or "")
