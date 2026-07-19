from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.db import deck_repository
from app.db.connection import db_session


class DeckCard(QFrame):
    study_clicked = Signal(int)
    browse_clicked = Signal(int)
    stats_clicked = Signal(int)
    history_clicked = Signal(int)
    settings_clicked = Signal(int)

    def __init__(self, deck, parent=None):
        super().__init__(parent)
        self.setObjectName("DeckCard")
        self.deck = deck

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)

        text_col = QVBoxLayout()
        name = QLabel(deck.name)
        name.setObjectName("DeckName")
        meta = QLabel(f"{deck.total_count} cards · {deck.source.replace('_', ' ')}")
        meta.setObjectName("DeckMeta")
        text_col.addWidget(name)
        text_col.addWidget(meta)
        layout.addLayout(text_col)
        layout.addStretch()

        if deck.due_count > 0:
            badge = QLabel(f"{deck.due_count} due")
            badge.setObjectName("DueBadge")
        else:
            badge = QLabel("caught up")
            badge.setObjectName("DueBadgeEmpty")
        layout.addWidget(badge)

        for text, obj_name, signal in [
            ("Browse", "Secondary", self.browse_clicked),
            ("Stats", "Secondary", self.stats_clicked),
            ("History", "Secondary", self.history_clicked),
            ("Settings", "Secondary", self.settings_clicked),
        ]:
            btn = QPushButton(text)
            btn.setObjectName(obj_name)
            btn.clicked.connect(lambda _, s=signal: s.emit(deck.id))
            layout.addWidget(btn)

        study_btn = QPushButton("Study")
        study_btn.setObjectName("Primary")
        study_btn.setEnabled(deck.total_count > 0)
        study_btn.clicked.connect(lambda: self.study_clicked.emit(deck.id))
        layout.addWidget(study_btn)


class DeckBrowser(QWidget):
    study_requested = Signal(int)
    browse_requested = Signal(int)
    stats_requested = Signal(int)
    history_requested = Signal(int)
    settings_requested = Signal(int)
    new_deck_requested = Signal()
    import_requested = Signal()
    preferences_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(16)

        header_row = QHBoxLayout()
        header = QLabel("Your Decks")
        header.setObjectName("AppTitle")
        header_row.addWidget(header)
        header_row.addStretch()

        settings_btn = QPushButton("Settings")
        settings_btn.setObjectName("Secondary")
        settings_btn.clicked.connect(self.preferences_requested.emit)
        header_row.addWidget(settings_btn)

        import_btn = QPushButton("Import PDF")
        import_btn.setObjectName("Secondary")
        import_btn.clicked.connect(self.import_requested.emit)
        header_row.addWidget(import_btn)

        new_deck_btn = QPushButton("+ New Deck")
        new_deck_btn.setObjectName("Primary")
        new_deck_btn.clicked.connect(self.new_deck_requested.emit)
        header_row.addWidget(new_deck_btn)
        outer.addLayout(header_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch()
        scroll.setWidget(self.list_container)
        outer.addWidget(scroll)

        self.refresh()

    def refresh(self) -> None:
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        with db_session() as conn:
            decks = deck_repository.list_decks(conn)

        for deck in decks:
            card = DeckCard(deck)
            card.study_clicked.connect(self.study_requested.emit)
            card.browse_clicked.connect(self.browse_requested.emit)
            card.stats_clicked.connect(self.stats_requested.emit)
            card.history_clicked.connect(self.history_requested.emit)
            card.settings_clicked.connect(self.settings_requested.emit)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

        if not decks:
            empty = QLabel("No decks yet. Import a PDF or create one manually to get started.")
            empty.setObjectName("DeckMeta")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty)
