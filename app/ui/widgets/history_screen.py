from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.db import deck_repository, history_repository
from app.db.connection import db_session

MODE_LABELS = {
    "flashcards": "Flashcards",
    "match": "Match",
    "learn": "Learn",
    "test": "Test",
}


class HistoryRow(QFrame):
    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.setObjectName("DeckCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        mode_label = QLabel(MODE_LABELS.get(entry.mode, entry.mode.title()))
        mode_label.setObjectName("TagChip")
        layout.addWidget(mode_label)

        text_col = QVBoxLayout()
        summary = QLabel(entry.summary)
        summary.setObjectName("DeckName")
        summary.setWordWrap(True)
        text_col.addWidget(summary)

        when = datetime.fromtimestamp(entry.completed_at).strftime("%b %d, %Y — %I:%M %p")
        when_label = QLabel(when)
        when_label.setObjectName("DeckMeta")
        text_col.addWidget(when_label)

        layout.addLayout(text_col, stretch=1)


class HistoryScreen(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.deck_id: int | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(16)

        top_row = QHBoxLayout()
        back_btn = QPushButton("< Study Options")
        back_btn.setObjectName("Secondary")
        back_btn.clicked.connect(self.back_requested.emit)
        top_row.addWidget(back_btn)
        self.title_label = QLabel("History")
        self.title_label.setObjectName("AppTitle")
        top_row.addWidget(self.title_label)
        top_row.addStretch()
        outer.addLayout(top_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch()
        scroll.setWidget(self.list_container)
        outer.addWidget(scroll, stretch=1)

    def open_deck(self, deck_id: int) -> None:
        self.deck_id = deck_id
        with db_session() as conn:
            deck = deck_repository.get_deck(conn, deck_id)
            entries = history_repository.list_history(conn, deck_id)

        self.title_label.setText(f"{deck.name} — History" if deck else "History")

        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        for entry in entries:
            self.list_layout.insertWidget(self.list_layout.count() - 1, HistoryRow(entry))

        if not entries:
            empty = QLabel("No study sessions yet. Practice with Flashcards, Match, Learn, or Test to build history.")
            empty.setObjectName("DeckMeta")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty)
