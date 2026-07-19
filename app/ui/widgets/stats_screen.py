from __future__ import annotations

import time

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.db import card_repository, deck_repository, review_repository
from app.db.connection import db_session

SECONDS_PER_DAY = 86400


class StatTile(QFrame):
    def __init__(self, value: str, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("DeckCard")
        layout = QVBoxLayout(self)
        value_label = QLabel(value)
        value_label.setObjectName("CardFront")
        label_label = QLabel(label)
        label_label.setObjectName("DeckMeta")
        layout.addWidget(value_label)
        layout.addWidget(label_label)


class ForecastBar(QWidget):
    def __init__(self, day_label: str, count: int, max_count: int, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        label = QLabel(day_label)
        label.setObjectName("DeckMeta")
        label.setFixedWidth(40)
        layout.addWidget(label)

        track = QFrame()
        track.setFixedHeight(14)
        track.setStyleSheet("background-color: #242836; border-radius: 7px;")
        track_layout = QHBoxLayout(track)
        track_layout.setContentsMargins(0, 0, 0, 0)
        fill_ratio = (count / max_count) if max_count else 0
        fill = QFrame()
        fill.setStyleSheet("background-color: #7c6cf0; border-radius: 7px;")
        track_layout.addWidget(fill, int(fill_ratio * 100))
        track_layout.addStretch(max(1, 100 - int(fill_ratio * 100)))
        layout.addWidget(track, stretch=1)

        count_label = QLabel(str(count))
        count_label.setObjectName("DeckMeta")
        count_label.setFixedWidth(30)
        layout.addWidget(count_label)


class StatsScreen(QWidget):
    back_requested = Signal()

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
        self.title_label = QLabel("")
        self.title_label.setObjectName("AppTitle")
        top_row.addWidget(self.title_label)
        top_row.addStretch()
        outer.addLayout(top_row)

        self.tile_row = QGridLayout()
        outer.addLayout(self.tile_row)

        forecast_label = QLabel("Next 7 days")
        forecast_label.setObjectName("DeckName")
        outer.addWidget(forecast_label)
        self.forecast_container = QVBoxLayout()
        outer.addLayout(self.forecast_container)

        outer.addStretch()

    def open_deck(self, deck_id: int) -> None:
        self.deck_id = deck_id
        now = int(time.time())

        with db_session() as conn:
            deck = deck_repository.get_deck(conn, deck_id)
            total = len(card_repository.list_cards(conn, deck_id))
            due_today = len(card_repository.get_due_cards(conn, deck_id, now))
            reviewed_today = review_repository.reviews_since(conn, deck_id, now - (now % SECONDS_PER_DAY))
            leeches = review_repository.leech_count(conn, deck_id)
            forecast = review_repository.due_forecast(conn, deck_id, now)
            review_day_set = set(review_repository.review_days(conn, deck_id))

        self.title_label.setText(f"{deck.name} — Stats")

        streak = 0
        today_bucket = now // SECONDS_PER_DAY
        day = today_bucket
        while day in review_day_set:
            streak += 1
            day -= 1

        while self.tile_row.count():
            item = self.tile_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tiles = [
            (str(total), "Total cards"),
            (str(due_today), "Due now"),
            (str(reviewed_today), "Reviewed today"),
            (f"{streak}d", "Study streak"),
            (str(leeches), "Leeches (8+ lapses)"),
        ]
        for i, (value, label) in enumerate(tiles):
            self.tile_row.addWidget(StatTile(value, label), 0, i)

        while self.forecast_container.count():
            item = self.forecast_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        max_count = max(forecast) if forecast else 0
        day_labels = ["Today", "+1d", "+2d", "+3d", "+4d", "+5d", "+6d"]
        for label, count in zip(day_labels, forecast):
            self.forecast_container.addWidget(ForecastBar(label, count, max_count))
