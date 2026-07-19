from app.db.models import CardReviewState
from app.sm2.scheduler import MIN_EASE_FACTOR, SECONDS_PER_DAY, schedule_review

NOW = 1_700_000_000


def fresh_state():
    return CardReviewState(card_id=1, ease_factor=2.5, interval_days=0, repetitions=0, due_at=NOW)


def test_first_good_review_sets_interval_to_one_day():
    state = schedule_review(fresh_state(), grade=4, now=NOW)
    assert state.repetitions == 1
    assert state.interval_days == 1
    assert state.due_at == NOW + SECONDS_PER_DAY


def test_second_good_review_sets_interval_to_six_days():
    state = schedule_review(fresh_state(), grade=4, now=NOW)
    state = schedule_review(state, grade=4, now=NOW)
    assert state.repetitions == 2
    assert state.interval_days == 6


def test_third_good_review_multiplies_by_ease_factor():
    state = fresh_state()
    state = schedule_review(state, grade=4, now=NOW)
    state = schedule_review(state, grade=4, now=NOW)
    ease_before_third = state.ease_factor
    state = schedule_review(state, grade=4, now=NOW)
    assert state.repetitions == 3
    assert state.interval_days == round(6 * ease_before_third)


def test_failing_grade_resets_repetitions_and_interval():
    state = fresh_state()
    state = schedule_review(state, grade=4, now=NOW)
    state = schedule_review(state, grade=4, now=NOW)
    state = schedule_review(state, grade=0, now=NOW)
    assert state.repetitions == 0
    assert state.interval_days == 1


def test_ease_factor_floors_at_1_3():
    state = fresh_state()
    for _ in range(20):
        state = schedule_review(state, grade=0, now=NOW)
    assert state.ease_factor == MIN_EASE_FACTOR


def test_easy_grade_increases_ease_factor():
    state = schedule_review(fresh_state(), grade=5, now=NOW)
    assert state.ease_factor > 2.5


def test_hard_grade_still_advances_but_lowers_ease_factor():
    state = schedule_review(fresh_state(), grade=3, now=NOW)
    assert state.repetitions == 1
    assert state.ease_factor < 2.5


def test_invalid_grade_raises():
    import pytest

    with pytest.raises(ValueError):
        schedule_review(fresh_state(), grade=6, now=NOW)


def test_last_reviewed_at_updates():
    state = schedule_review(fresh_state(), grade=4, now=NOW)
    assert state.last_reviewed_at == NOW


def test_lapse_only_counted_after_prior_success():
    state = schedule_review(fresh_state(), grade=0, now=NOW)
    assert state.lapses == 0, "failing a never-reviewed card is not a lapse"

    state = schedule_review(fresh_state(), grade=4, now=NOW)
    state = schedule_review(state, grade=0, now=NOW)
    assert state.lapses == 1
