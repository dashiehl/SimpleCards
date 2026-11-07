from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

GRID_COLUMNS = 2

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
        self.setMinimumHeight(150)
        self.setMaximumHeight(175)
        self.deck = deck

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 14)
        layout.setSpacing(8)

        top = QHBoxLayout()
        name = QLabel(deck.name)
        name.setObjectName("DeckName")
        name.setWordWrap(True)
        top.addWidget(name, stretch=1)
        if deck.due_count > 0:
            badge = QLabel(f"{deck.due_count} due")
            badge.setObjectName("DueBadge")
        else:
            badge = QLabel("caught up")
            badge.setObjectName("DueBadgeEmpty")
        top.addWidget(badge, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)

        meta = QLabel(f"{deck.total_count} cards · {deck.source.replace('_', ' ')}")
        meta.setObjectName("DeckMeta")
        layout.addWidget(meta)

        # Share of the deck that is NOT due right now (i.e. reviewed and scheduled ahead).
        progress = QProgressBar()
        progress.setRange(0, max(1, deck.total_count))
        progress.setValue(max(0, deck.total_count - deck.due_count))
        progress.setTextVisible(False)
        progress.setToolTip("Cards reviewed and scheduled ahead")
        layout.addWidget(progress)
        layout.addStretch()

        bottom = QHBoxLayout()
        bottom.setSpacing(2)
        for text, signal in [
            ("Browse", self.browse_clicked),
            ("Stats", self.stats_clicked),
            ("History", self.history_clicked),
            ("Settings", self.settings_clicked),
        ]:
            btn = QPushButton(text)
            btn.setObjectName("Ghost")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, s=signal: s.emit(deck.id))
            bottom.addWidget(btn)
        bottom.addStretch()

        study_btn = QPushButton("Study")
        study_btn.setObjectName("Primary")
        study_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        study_btn.setEnabled(deck.total_count > 0)
        study_btn.clicked.connect(lambda: self.study_clicked.emit(deck.id))
        bottom.addWidget(study_btn)
        layout.addLayout(bottom)


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
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        header = QLabel("Your Decks")
        header.setObjectName("AppTitle")
        title_col.addWidget(header)
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("Subtitle")
        self.summary_label.setContentsMargins(8, 0, 0, 0)
        title_col.addWidget(self.summary_label)
        header_row.addLayout(title_col)
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
        container_layout = QVBoxLayout(self.list_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout = QGridLayout()
        self.list_layout.setSpacing(14)
        container_layout.addLayout(self.list_layout)
        container_layout.addStretch()
        scroll.setWidget(self.list_container)
        outer.addWidget(scroll)

        self.refresh()

    def refresh(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        with db_session() as conn:
            decks = deck_repository.list_decks(conn)

        for i, deck in enumerate(decks):
            card = DeckCard(deck)
            card.study_clicked.connect(self.study_requested.emit)
            card.browse_clicked.connect(self.browse_requested.emit)
            card.stats_clicked.connect(self.stats_requested.emit)
            card.history_clicked.connect(self.history_requested.emit)
            card.settings_clicked.connect(self.settings_requested.emit)
            self.list_layout.addWidget(card, i // GRID_COLUMNS, i % GRID_COLUMNS)
        for col in range(GRID_COLUMNS):
            self.list_layout.setColumnStretch(col, 1)

        total_due = sum(d.due_count for d in decks)
        if not decks:
            self.summary_label.setText("")
            empty = QLabel("No decks yet. Import a PDF or create one manually to get started.")
            empty.setObjectName("DeckMeta")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setContentsMargins(0, 60, 0, 0)
            self.list_layout.addWidget(empty, 0, 0, 1, GRID_COLUMNS)
        elif total_due:
            self.summary_label.setText(f"{total_due} cards due across {len(decks)} decks")
        else:
            self.summary_label.setText(f"All caught up across {len(decks)} decks")
