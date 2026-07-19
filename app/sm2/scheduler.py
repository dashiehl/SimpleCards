from __future__ import annotations

from app.db.models import CardReviewState

SECONDS_PER_DAY = 86400
MIN_EASE_FACTOR = 1.3


def schedule_review(state: CardReviewState, grade: int, now: int) -> CardReviewState:
    """Textbook SM-2. `grade` is a 0-5 quality rating; `now` is epoch seconds."""
    if not 0 <= grade <= 5:
        raise ValueError(f"grade must be 0-5, got {grade}")

    lapses = state.lapses
    if grade < 3:
        if state.repetitions > 0:
            lapses += 1
        repetitions = 0
        interval_days = 1
    else:
        if state.repetitions == 0:
            interval_days = 1
        elif state.repetitions == 1:
            interval_days = 6
        else:
            interval_days = round(state.interval_days * state.ease_factor)
        repetitions = state.repetitions + 1

    ease_factor = state.ease_factor + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    ease_factor = max(MIN_EASE_FACTOR, ease_factor)

    return CardReviewState(
        card_id=state.card_id,
        ease_factor=ease_factor,
        interval_days=interval_days,
        repetitions=repetitions,
        lapses=lapses,
        due_at=now + interval_days * SECONDS_PER_DAY,
        last_reviewed_at=now,
    )
