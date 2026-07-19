from app.db import card_repository, deck_repository, learn_repository
from app.db.connection import get_connection, init_db


def make_conn(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return get_connection(db_path)


def make_deck_with_card(conn):
    deck = deck_repository.create_deck(conn, "Deck")
    card = card_repository.create_card(conn, deck_id=deck.id, front="Term", back="Definition")
    return deck.id, card.id


def test_missing_cards_are_implicitly_stage1(tmp_path):
    conn = make_conn(tmp_path)
    deck_id, _ = make_deck_with_card(conn)
    assert learn_repository.get_progress_map(conn, deck_id) == {}


def test_set_stage_inserts_and_updates(tmp_path):
    conn = make_conn(tmp_path)
    deck_id, card_id = make_deck_with_card(conn)

    learn_repository.set_stage(conn, deck_id, card_id, stage="stage2")
    assert learn_repository.get_progress_map(conn, deck_id) == {card_id: "stage2"}

    learn_repository.set_stage(conn, deck_id, card_id, stage="mastered")
    assert learn_repository.get_progress_map(conn, deck_id) == {card_id: "mastered"}


def test_reset_progress_clears_only_that_deck(tmp_path):
    conn = make_conn(tmp_path)
    deck_id_1, card_id_1 = make_deck_with_card(conn)
    deck_id_2, card_id_2 = make_deck_with_card(conn)

    learn_repository.set_stage(conn, deck_id_1, card_id_1, stage="stage2")
    learn_repository.set_stage(conn, deck_id_2, card_id_2, stage="stage2")

    learn_repository.reset_progress(conn, deck_id_1)

    assert learn_repository.get_progress_map(conn, deck_id_1) == {}
    assert learn_repository.get_progress_map(conn, deck_id_2) == {card_id_2: "stage2"}
