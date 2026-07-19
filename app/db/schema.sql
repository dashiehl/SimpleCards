PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS decks (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    source        TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'pdf_import', 'ai_generated')),
    front_fields  TEXT NOT NULL DEFAULT '["front"]',
    back_fields   TEXT NOT NULL DEFAULT '["back"]',
    created_at    INTEGER NOT NULL,
    updated_at    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS cards (
    id           INTEGER PRIMARY KEY,
    deck_id      INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL DEFAULT 'basic' CHECK (kind IN ('basic', 'multi_field', 'cloze', 'image')),
    front        TEXT NOT NULL,
    back         TEXT,
    extra_fields TEXT NOT NULL DEFAULT '{}',
    tags         TEXT NOT NULL DEFAULT '[]',
    source_ref   TEXT,
    created_at   INTEGER NOT NULL,
    updated_at   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cards_deck_id ON cards(deck_id);

CREATE TABLE IF NOT EXISTS card_review_state (
    card_id          INTEGER PRIMARY KEY REFERENCES cards(id) ON DELETE CASCADE,
    ease_factor      REAL NOT NULL DEFAULT 2.5,
    interval_days    INTEGER NOT NULL DEFAULT 0,
    repetitions      INTEGER NOT NULL DEFAULT 0,
    lapses           INTEGER NOT NULL DEFAULT 0,
    due_at           INTEGER NOT NULL,
    last_reviewed_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_card_review_state_due_at ON card_review_state(due_at);

CREATE TABLE IF NOT EXISTS review_log (
    id                   INTEGER PRIMARY KEY,
    card_id              INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    reviewed_at          INTEGER NOT NULL,
    grade                INTEGER NOT NULL,
    ease_factor_after    REAL NOT NULL,
    interval_days_after  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_review_log_card_id ON review_log(card_id, reviewed_at);

CREATE TABLE IF NOT EXISTS learn_progress (
    card_id    INTEGER PRIMARY KEY REFERENCES cards(id) ON DELETE CASCADE,
    deck_id    INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    stage      TEXT NOT NULL DEFAULT 'stage1' CHECK (stage IN ('stage1', 'stage2', 'mastered')),
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_learn_progress_deck_id ON learn_progress(deck_id);

CREATE TABLE IF NOT EXISTS session_history (
    id           INTEGER PRIMARY KEY,
    deck_id      INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    mode         TEXT NOT NULL CHECK (mode IN ('flashcards', 'match', 'learn', 'test')),
    summary      TEXT NOT NULL DEFAULT '',
    completed_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_session_history_deck_id ON session_history(deck_id, completed_at);
