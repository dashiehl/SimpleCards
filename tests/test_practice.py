from app.db.models import Card
from app.study_modes.practice import fuzzy_match, pick_distractors, prompt_text


def make_card(id_, front, back="", **extra_fields):
    return Card(id=id_, deck_id=1, front=front, back=back, extra_fields=extra_fields)


def test_prompt_text_joins_nonempty_fields():
    card = make_card(1, "Ad Hominem", "Attacks the person", example="quote here")
    assert prompt_text(card, ["front"]) == "Ad Hominem"
    assert prompt_text(card, ["back", "example"]) == "Attacks the person\nquote here"


def test_prompt_text_skips_empty_fields():
    card = make_card(1, "Term", "")
    assert prompt_text(card, ["front", "back"]) == "Term"


def test_pick_distractors_excludes_correct_card_and_dedupes():
    correct = make_card(1, "Straw Man", "def1")
    cards = [
        correct,
        make_card(2, "Straw Man", "def1"),  # duplicate text of the correct answer, must be excluded
        make_card(3, "Red Herring", "def2"),
        make_card(4, "Ad Hominem", "def3"),
        make_card(5, "Red Herring", "def2"),  # duplicate of card 3's text
    ]
    distractors = pick_distractors(cards, correct, ["front"], count=3)
    assert "Straw Man" not in distractors
    assert len(distractors) == len(set(distractors))
    assert len(distractors) <= 2  # only 2 unique non-correct texts exist


def test_pick_distractors_limits_to_count():
    correct = make_card(1, "A", "1")
    cards = [correct] + [make_card(i, f"Term{i}", str(i)) for i in range(2, 10)]
    distractors = pick_distractors(cards, correct, ["front"], count=3)
    assert len(distractors) == 3


def test_fuzzy_match_exact():
    assert fuzzy_match("Ad Hominem", "Ad Hominem")


def test_fuzzy_match_case_and_whitespace_insensitive():
    assert fuzzy_match("  ad hominem  ", "Ad Hominem")


def test_fuzzy_match_tolerates_minor_typo():
    assert fuzzy_match("Ad Hominim", "Ad Hominem")


def test_fuzzy_match_rejects_unrelated_text():
    assert not fuzzy_match("Straw Man", "Ad Hominem")


def test_fuzzy_match_rejects_empty_input():
    assert not fuzzy_match("", "Ad Hominem")
