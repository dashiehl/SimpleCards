from __future__ import annotations

import random
import time

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.db import card_repository, deck_repository, history_repository
from app.db.connection import db_session
from app.study_modes.practice import prompt_text

MAX_PAIRS = 8
MIN_CARDS = 2
MISMATCH_FLASH_MS = 500


class MatchTile(QPushButton):
    def __init__(self, card_id: int, text: str, parent=None):
        super().__init__(text, parent)
        self.card_id = card_id
        self.setObjectName("MatchTile")
        self.setProperty("matchState", "default")
        self.setMinimumHeight(70)

    def set_state(self, state: str) -> None:
        self.setProperty("matchState", state)
        self.style().unpolish(self)
        self.style().polish(self)


class MatchScreen(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.deck_id: int | None = None
        self.total_pairs = 0
        self.matched_pairs = 0
        self._selected: list[MatchTile] = []
        self._locked = False
        self._start_time = 0.0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(16)

        top_row = QHBoxLayout()
        back_btn = QPushButton("< Study Options")
        back_btn.setObjectName("Secondary")
        back_btn.clicked.connect(self.back_requested.emit)
        top_row.addWidget(back_btn)
        self.title_label = QLabel("Match")
        self.title_label.setObjectName("AppTitle")
        top_row.addWidget(self.title_label)
        top_row.addStretch()
        self.timer_label = QLabel("0.0s")
        self.timer_label.setObjectName("DeckMeta")
        top_row.addWidget(self.timer_label)
        outer.addLayout(top_row)

        self.message_label = QLabel("")
        self.message_label.setObjectName("DeckMeta")
        outer.addWidget(self.message_label)

        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setSpacing(10)
        outer.addWidget(self.grid_container, stretch=1)

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.play_again_btn = QPushButton("Play Again")
        self.play_again_btn.setObjectName("Primary")
        self.play_again_btn.hide()
        self.play_again_btn.clicked.connect(lambda: self.start(self.deck_id))
        bottom_row.addWidget(self.play_again_btn)
        outer.addLayout(bottom_row)

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(100)
        self._tick_timer.timeout.connect(self._update_timer_label)

    def start(self, deck_id: int) -> None:
        self.deck_id = deck_id
        self.play_again_btn.hide()
        self._selected = []
        self._locked = False

        with db_session() as conn:
            deck = deck_repository.get_deck(conn, deck_id)
            cards = card_repository.list_cards(conn, deck_id)

        self.title_label.setText(f"{deck.name} — Match")
        self._clear_grid()

        if len(cards) < MIN_CARDS:
            self.message_label.setText(f"Match needs at least {MIN_CARDS} cards in this deck.")
            self.grid_container.hide()
            self._tick_timer.stop()
            return
        self.grid_container.show()

        sample = random.sample(cards, min(MAX_PAIRS, len(cards)))
        tiles = []
        for card in sample:
            front_text = prompt_text(card, deck.front_fields) or card.front
            back_text = prompt_text(card, deck.back_fields) or (card.back or "")
            tiles.append((card.id, front_text))
            tiles.append((card.id, back_text))
        random.shuffle(tiles)

        self.total_pairs = len(sample)
        self.matched_pairs = 0
        self.message_label.setText(f"Match all {self.total_pairs} pairs.")

        columns = 4
        for i, (card_id, text) in enumerate(tiles):
            tile = MatchTile(card_id, text)
            tile.clicked.connect(lambda _=False, t=tile: self._on_tile_clicked(t))
            self.grid.addWidget(tile, i // columns, i % columns)

        self._start_time = time.time()
        self.timer_label.setText("0.0s")
        self._tick_timer.start()

    def _clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _update_timer_label(self) -> None:
        elapsed = time.time() - self._start_time
        self.timer_label.setText(f"{elapsed:.1f}s")

    def _on_tile_clicked(self, tile: MatchTile) -> None:
        if self._locked or tile in self._selected or tile.property("matchState") == "matched":
            return

        tile.set_state("selected")
        self._selected.append(tile)
        if len(self._selected) < 2:
            return

        first, second = self._selected
        self._selected = []

        if first.card_id == second.card_id:
            first.set_state("matched")
            second.set_state("matched")
            first.setEnabled(False)
            second.setEnabled(False)
            self.matched_pairs += 1
            if self.matched_pairs >= self.total_pairs:
                self._finish()
        else:
            self._locked = True
            first.set_state("wrong")
            second.set_state("wrong")
            QTimer.singleShot(MISMATCH_FLASH_MS, lambda: self._reset_pair(first, second))

    def _reset_pair(self, first: MatchTile, second: MatchTile) -> None:
        first.set_state("default")
        second.set_state("default")
        self._locked = False

    def _finish(self) -> None:
        self._tick_timer.stop()
        elapsed = time.time() - self._start_time
        self.message_label.setText(f"Solved all {self.total_pairs} pairs in {elapsed:.1f}s!")
        self.play_again_btn.show()
        with db_session() as conn:
            history_repository.log_session(
                conn, self.deck_id, "match", f"Matched {self.total_pairs} pairs in {elapsed:.1f}s",
            )
