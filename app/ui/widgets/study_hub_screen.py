from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.db import deck_repository
from app.db.connection import db_session


class ModeTile(QFrame):
    clicked = Signal()

    def __init__(self, title: str, description: str, button_text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ModeTile")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        name = QLabel(title)
        name.setObjectName("DeckName")
        layout.addWidget(name)

        desc = QLabel(description)
        desc.setObjectName("ModeTileDescription")
        desc.setWordWrap(True)
        layout.addWidget(desc, stretch=1)

        btn = QPushButton(button_text)
        btn.setObjectName("Primary")
        btn.clicked.connect(self.clicked.emit)
        layout.addWidget(btn)


class StudyHub(QWidget):
    back_requested = Signal()
    flashcards_requested = Signal(int)
    match_requested = Signal(int)
    learn_requested = Signal(int)
    test_requested = Signal(int)
    history_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.deck_id: int | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(16)

        top_row = QHBoxLayout()
        back_btn = QPushButton("< Decks")
        back_btn.setObjectName("Secondary")
        back_btn.clicked.connect(self.back_requested.emit)
        top_row.addWidget(back_btn)
        self.title_label = QLabel("Study")
        self.title_label.setObjectName("AppTitle")
        top_row.addWidget(self.title_label)
        top_row.addStretch()
        history_btn = QPushButton("History")
        history_btn.setObjectName("Secondary")
        history_btn.clicked.connect(lambda: self.history_requested.emit(self.deck_id))
        top_row.addWidget(history_btn)
        outer.addLayout(top_row)

        subtitle = QLabel("Choose how you'd like to study this deck.")
        subtitle.setObjectName("DeckMeta")
        outer.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(16)
        outer.addLayout(grid, stretch=1)

        flashcards_tile = ModeTile(
            "Flashcards", "Flip through cards and grade yourself — feeds your spaced-repetition schedule.",
            "Study Flashcards",
        )
        flashcards_tile.clicked.connect(lambda: self.flashcards_requested.emit(self.deck_id))
        grid.addWidget(flashcards_tile, 0, 0)

        learn_tile = ModeTile(
            "Learn", "Multiple choice first, then typed recall. Remembers your progress between sessions.",
            "Start Learn",
        )
        learn_tile.clicked.connect(lambda: self.learn_requested.emit(self.deck_id))
        grid.addWidget(learn_tile, 0, 1)

        match_tile = ModeTile(
            "Match", "Race the clock pairing up terms and definitions.",
            "Play Match",
        )
        match_tile.clicked.connect(lambda: self.match_requested.emit(self.deck_id))
        grid.addWidget(match_tile, 1, 0)

        test_tile = ModeTile(
            "Test", "Build a custom practice test — multiple choice, true/false, written, and matching.",
            "Build a Test",
        )
        test_tile.clicked.connect(lambda: self.test_requested.emit(self.deck_id))
        grid.addWidget(test_tile, 1, 1)

        outer.addStretch()

    def open_deck(self, deck_id: int) -> None:
        self.deck_id = deck_id
        with db_session() as conn:
            deck = deck_repository.get_deck(conn, deck_id)
        self.title_label.setText(deck.name if deck else "Study")
