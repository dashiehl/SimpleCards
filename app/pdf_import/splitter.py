from __future__ import annotations

import re
from collections import Counter, defaultdict

from app.pdf_import.candidate import CandidateCard
from app.pdf_import.extractor import TextSpan

TERM_DEF_RE = re.compile(r"^\s*([A-Za-z][\w '\-]{1,40})\s*[:—–-]\s+(.{5,})$")

BREADCRUMB_RE = re.compile(r"^.+[·•]\s*\d+\s*/\s*\d+\s*$")
PAGE_FRACTION_RE = re.compile(r"^\d+\s*/\s*\d+$")


def _body_style(spans: list[TextSpan]) -> tuple[str, float]:
    """The (font, size) combo with the most total characters is treated as body text."""
    totals: Counter[tuple[str, float]] = Counter()
    for s in spans:
        totals[(s.font, s.size)] += len(s.text)
    return totals.most_common(1)[0][0]


def _detect_name_style(spans: list[TextSpan], body_size: float) -> tuple[str, float] | None:
    """Find the (font, size) combo most likely to mark a term/heading: mid-size, short spans,
    appearing frequently (a real "one per card" label recurs far more than a one-per-page header)."""
    counts: Counter[tuple[str, float]] = Counter()
    word_totals: dict[tuple[str, float], int] = defaultdict(int)
    for s in spans:
        key = (s.font, s.size)
        counts[key] += 1
        word_totals[key] += len(s.text.split())

    candidates = []
    for key, count in counts.items():
        font, size = key
        if size <= body_size or size > body_size * 2.2:
            continue
        avg_words = word_totals[key] / count
        if avg_words > 5 or count < 3:
            continue
        candidates.append((count, key))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def split_structured_glossary(spans: list[TextSpan]) -> list[CandidateCard]:
    """Heuristic #1: detect a recurring "Name / forms line / definition / example" pattern
    driven by font metadata (works well for glossary/field-guide style PDFs)."""
    if not spans:
        return []
    body_font, body_size = _body_style(spans)
    name_style = _detect_name_style(spans, body_size)
    if name_style is None:
        return []
    name_font, name_size = name_style

    candidates: list[CandidateCard] = []
    current: CandidateCard | None = None
    state = "seek_name"

    for s in spans:
        is_name = s.font == name_font and s.size == name_size
        if is_name:
            if current is not None:
                candidates.append(current)
            current = CandidateCard(
                front=s.text, kind="multi_field",
                source_ref=f"page {s.page_number + 1}",
            )
            state = "seek_forms"
            continue

        if current is None:
            continue

        if state == "seek_forms":
            current.extra_fields["forms"] = s.text
            state = "body"
            continue

        state = "body"
        if s.text.startswith('"') or current.extra_fields.get("_in_example"):
            current.extra_fields["_in_example"] = True
            current.extra_fields["example"] = (current.extra_fields.get("example", "") + " " + s.text).strip()
        else:
            current.back = ((current.back or "") + " " + s.text).strip()

    if current is not None:
        candidates.append(current)

    for c in candidates:
        c.extra_fields.pop("_in_example", None)
        example = c.extra_fields.get("example")
        if example:
            c.extra_fields["example"] = example.strip('"').strip()
        if not c.back:
            c.back = c.extra_fields.get("example", "")
        c.confidence = 0.9 if c.extra_fields.get("forms") and c.back else 0.5

    return [c for c in candidates if c.front and c.back]


def _label_key(text: str) -> str | None:
    """Recognize short ALL-CAPS caption spans like "EXAMPLE" or "WHEN TO USE IT" as a
    named section switch, without needing font metadata for them specifically."""
    stripped = text.strip()
    if not stripped or not stripped.isupper() or len(stripped) > 30:
        return None
    words = stripped.split()
    if not (1 <= len(words) <= 4):
        return None
    return stripped.lower().replace(" ", "_")


def split_name_body_example(spans: list[TextSpan]) -> list[CandidateCard]:
    """Heuristic: detect a recurring heading style (one per card, possibly several cards
    per page) and bucket everything until the next heading into fields. Handles decks with
    no explicit "forms" line, multiple cards per page, quoted/italic examples, numbered
    steps, and ALL-CAPS section captions (EXAMPLE, WHEN TO USE IT, ...) — patterns common
    in field-guide and framework-card style PDFs that split_structured_glossary misses."""
    if not spans:
        return []
    body_font, body_size = _body_style(spans)
    name_style = _detect_name_style(spans, body_size)
    if name_style is None:
        return []
    name_font, name_size = name_style

    candidates: list[CandidateCard] = []
    current: CandidateCard | None = None
    section = "back"
    pending_step: str | None = None

    for s in spans:
        is_name = s.font == name_font and s.size == name_size
        if is_name:
            if current is not None:
                candidates.append(current)
            current = CandidateCard(front=s.text, kind="multi_field", source_ref=f"page {s.page_number + 1}")
            section = "back"
            pending_step = None
            continue

        if current is None:
            continue

        text = s.text.strip()
        if not text:
            continue

        if BREADCRUMB_RE.match(text) or PAGE_FRACTION_RE.match(text):
            continue

        label = _label_key(text)
        if label:
            section = label
            continue

        if pending_step is not None:
            steps = current.extra_fields.get("steps", "")
            current.extra_fields["steps"] = f"{steps}\n{pending_step}. {text}".strip()
            pending_step = None
            continue

        if text.isdigit() and len(text) <= 2:
            pending_step = text
            continue

        target_section = section
        looks_like_quote = s.is_italic or text.startswith(('"', "'", "“"))
        if section == "back" and looks_like_quote and current.back:
            target_section = "example"

        if target_section == "back":
            current.back = f"{current.back} {text}".strip() if current.back else text
        else:
            existing = current.extra_fields.get(target_section, "")
            current.extra_fields[target_section] = f"{existing} {text}".strip() if existing else text

    if current is not None:
        candidates.append(current)

    for c in candidates:
        example = c.extra_fields.get("example")
        if example:
            c.extra_fields["example"] = example.strip('"').strip()
        if not c.back:
            c.back = c.extra_fields.get("example", "")
        c.confidence = 0.85 if (c.back and c.extra_fields) else (0.6 if c.back else 0.3)

    return [c for c in candidates if c.front and (c.back or c.extra_fields)]


def split_term_definition_pattern(spans: list[TextSpan]) -> list[CandidateCard]:
    """Heuristic #2: lines matching `TERM: definition` / `TERM — definition`."""
    candidates = []
    for s in spans:
        match = TERM_DEF_RE.match(s.text)
        if match:
            candidates.append(CandidateCard(
                front=match.group(1).strip(), back=match.group(2).strip(),
                source_ref=f"page {s.page_number + 1}", confidence=0.7,
            ))
    return candidates


def split_bullet_groups(spans: list[TextSpan]) -> list[CandidateCard]:
    """Heuristic #3: one card per bulleted line, grouped by page (front = truncated text)."""
    candidates = []
    for s in spans:
        text = s.text.lstrip("•-* \t")
        if text != s.text and len(text) > 3:
            words = text.split(" ", 1)
            front = words[0]
            back = words[1] if len(words) > 1 else text
            candidates.append(CandidateCard(
                front=front, back=back, source_ref=f"page {s.page_number + 1}", confidence=0.4,
            ))
    return candidates


def split_whole_page_fallback(spans: list[TextSpan]) -> list[CandidateCard]:
    """Heuristic #4: no structure detected — one card per page with all its text as the back."""
    by_page: dict[int, list[str]] = defaultdict(list)
    for s in spans:
        by_page[s.page_number].append(s.text)
    return [
        CandidateCard(
            front=f"Page {page + 1}", back=" ".join(texts),
            source_ref=f"page {page + 1}", confidence=0.2,
        )
        for page, texts in by_page.items() if texts
    ]


def split_into_candidates(spans: list[TextSpan], mode: str = "auto") -> list[CandidateCard]:
    """Run heuristics in order of specificity; use the first one that yields a healthy result.

    `mode` lets the caller force a particular style instead of auto-detecting:
    - "simple": front/back only, skipping the multi-field glossary heuristic.
    - "detailed": prefer the multi-field glossary heuristic, accepting fewer matches.
    - "auto" (default): try every heuristic in order of specificity.
    """
    if mode == "simple":
        for splitter, min_count in (
            (split_term_definition_pattern, 3),
            (split_bullet_groups, 3),
        ):
            result = splitter(spans)
            if len(result) >= min_count:
                return result
        return split_whole_page_fallback(spans)

    if mode == "detailed":
        for splitter in (split_name_body_example, split_structured_glossary):
            result = splitter(spans)
            if result:
                return result
        return split_whole_page_fallback(spans)

    for splitter, min_count in (
        (split_name_body_example, 3),
        (split_structured_glossary, 3),
        (split_term_definition_pattern, 3),
        (split_bullet_groups, 3),
    ):
        result = splitter(spans)
        if len(result) >= min_count:
            return result
    return split_whole_page_fallback(spans)
