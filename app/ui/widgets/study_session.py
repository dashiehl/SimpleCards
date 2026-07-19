from __future__ import annotations

import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.cards.cloze import has_cloze_markers, masked_text, revealed_text
from app.db import card_repository, deck_repository, review_repository
from app.db.connection import db_session
from app.sm2.grading import BUTTON_TO_GRADE
from app.ui.widgets.card_flip_widget import CardFlipWidget
from app.ui.widgets.field_panel import CardFacePanel


class StudySession(QWidget):
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.deck = None
        self.queue: list = []
        self.index = 0
        self.revealed = False
        self._undo_state = None  # (card_id, previous_review_state)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(16)

        top_row = QHBoxLayout()
        back_btn = QPushButton("< Decks")
        back_btn.setObjectName("Secondary")
        back_btn.clicked.connect(self.finished.emit)
        top_row.addWidget(back_btn)

        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setObjectName("Secondary")
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self._undo)
        top_row.addWidget(self.undo_btn)

        top_row.addStretch()
        self.leech_badge = QLabel("Leech")
        self.leech_badge.setObjectName("LeechBadge")
        self.leech_badge.hide()
        top_row.addWidget(self.leech_badge)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("DeckMeta")
        top_row.addWidget(self.progress_label)
        outer.addLayout(top_row)

        self.card = CardFlipWidget()
        self.card.mousePressEvent = self._on_card_clicked
        outer.addWidget(self.card, stretch=1)

        self.front_panel = CardFacePanel()
        self.back_panel = CardFacePanel()
        self.card.content_layout.addWidget(self.front_panel)
        self.card.content_layout.addWidget(self.back_panel)

        self.hint_label = QLabel("Click the card or press Space to reveal")
        self.hint_label.setObjectName("FlipHint")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.hint_label)

        self.grade_row = QHBoxLayout()
        self.grade_row.setSpacing(10)
        self._grade_buttons = {}
        for key, label, obj_name in [
            ("again", "Again (1)", "GradeAgain"), ("hard", "Hard (2)", "GradeHard"),
            ("good", "Good (3)", "GradeGood"), ("easy", "Easy (4)", "GradeEasy"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj_name)
            btn.clicked.connect(lambda _, k=key: self._grade(k))
            btn.setEnabled(False)
            self._grade_buttons[key] = btn
            self.grade_row.addWidget(btn)
        outer.addLayout(self.grade_row)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def start(self, deck_id: int) -> None:
        with db_session() as conn:
            self.deck = deck_repository.get_deck(conn, deck_id)
            self.queue = card_repository.get_due_cards(conn, deck_id)
        self.index = 0
        self._undo_state = None
        self.undo_btn.setEnabled(False)
        self._show_current()

    def _fields_for(self, card, field_keys: list[str], is_front: bool) -> list[tuple[str, str]]:
        if card.kind == "cloze":
            text = card.extra_fields.get("cloze_text", card.front)
            if has_cloze_markers(text):
                shown = masked_text(text) if is_front else revealed_text(text)
                return [("cloze_text", shown)]
        return [(key, card.field_value(key)) for key in field_keys]

    def _show_current(self) -> None:
        self.revealed = False
        self.card.content_layout.setCurrentWidget(self.front_panel)
        self.hint_label.setText("Click the card or press Space to reveal")
        for btn in self._grade_buttons.values():
            btn.setEnabled(False)

        if self.index >= len(self.queue):
            self.front_panel.set_fields([("front", "All caught up! 🎉")])
            self.back_panel.set_fields([])
            self.progress_label.setText("")
            self.leech_badge.hide()
            return

        current = self.queue[self.index]
        self.front_panel.set_fields(self._fields_for(current, self.deck.front_fields, is_front=True))
        self.back_panel.set_fields(self._fields_for(current, self.deck.back_fields, is_front=False))
        self.progress_label.setText(f"{self.index + 1} / {len(self.queue)}")

        with db_session() as conn:
            state = card_repository.get_review_state(conn, current.id)
        self.leech_badge.setVisible(bool(state and state.is_leech))

    def _on_card_clicked(self, event) -> None:
        self._reveal()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space:
            self._reveal()
        elif event.key() == Qt.Key.Key_1:
            self._grade("again")
        elif event.key() == Qt.Key.Key_2:
            self._grade("hard")
        elif event.key() == Qt.Key.Key_3:
            self._grade("good")
        elif event.key() == Qt.Key.Key_4:
            self._grade("easy")
        elif event.key() == Qt.Key.Key_Z and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._undo()
        else:
            super().keyPressEvent(event)

    def _reveal(self) -> None:
        if self.revealed or self.index >= len(self.queue):
            return
        self.revealed = True
        self.hint_label.setText("")
        self.card.flip_to(lambda: self.card.content_layout.setCurrentWidget(self.back_panel))
        for btn in self._grade_buttons.values():
            btn.setEnabled(True)

    def _grade(self, key: str) -> None:
        if not self.revealed or self.index >= len(self.queue):
            return
        grade = BUTTON_TO_GRADE[key]
        current = self.queue[self.index]
        with db_session() as conn:
            old_state, _ = review_repository.apply_grade(conn, current.id, grade, int(time.time()))
        self._undo_state = (current.id, old_state)
        self.undo_btn.setEnabled(True)
        self.index += 1
        self._show_current()

    def _undo(self) -> None:
        if self._undo_state is None or self.index == 0:
            return
        card_id, old_state = self._undo_state
        with db_session() as conn:
            review_repository.restore_state(conn, old_state)
        self._undo_state = None
        self.undo_btn.setEnabled(False)
        self.index -= 1
        self._show_current()
