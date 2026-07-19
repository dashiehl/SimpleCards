from __future__ import annotations

import random

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QStackedLayout, QVBoxLayout, QWidget,
)

from app.db import card_repository, deck_repository, history_repository, learn_repository
from app.db.connection import db_session
from app.study_modes.practice import fuzzy_match, pick_distractors, prompt_text

MIN_CARDS = 4
WRONG_ANSWER_PAUSE_MS = 1100


class LearnScreen(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.deck = None
        self.all_cards: list = []
        self.stage1_queue: list = []
        self.stage2_queue: list = []
        self.mastered_count = 0
        self.current_card = None
        self._locked = False
        self._answered_count = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(16)

        top_row = QHBoxLayout()
        back_btn = QPushButton("< Study Options")
        back_btn.setObjectName("Secondary")
        back_btn.clicked.connect(self._leave)
        top_row.addWidget(back_btn)
        self.title_label = QLabel("Learn")
        self.title_label.setObjectName("AppTitle")
        top_row.addWidget(self.title_label)
        top_row.addStretch()
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("DeckMeta")
        top_row.addWidget(self.progress_label)
        outer.addLayout(top_row)

        self.message_label = QLabel("")
        self.message_label.setObjectName("DeckMeta")
        self.message_label.setWordWrap(True)
        outer.addWidget(self.message_label)

        self.pages = QStackedLayout()
        outer.addLayout(self.pages, stretch=1)

        self.pages.addWidget(self._build_stage1_page())
        self.pages.addWidget(self._build_stage2_page())
        self.pages.addWidget(self._build_done_page())

    # -- page builders --------------------------------------------------

    def _build_stage1_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)

        self.stage1_prompt = QLabel("")
        self.stage1_prompt.setObjectName("CardFront")
        self.stage1_prompt.setWordWrap(True)
        layout.addWidget(self.stage1_prompt)

        self.stage1_buttons = []
        for _ in range(4):
            btn = QPushButton("")
            btn.setObjectName("Secondary")
            btn.clicked.connect(lambda _, b=btn: self._on_stage1_answer(b))
            layout.addWidget(btn)
            self.stage1_buttons.append(btn)

        layout.addStretch()
        return page

    def _build_stage2_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        self.stage2_prompt = QLabel("")
        self.stage2_prompt.setObjectName("CardFront")
        self.stage2_prompt.setWordWrap(True)
        layout.addWidget(self.stage2_prompt)

        self.stage2_input = QLineEdit()
        self.stage2_input.setPlaceholderText("Type the answer...")
        self.stage2_input.returnPressed.connect(self._on_stage2_submit)
        layout.addWidget(self.stage2_input)

        check_btn = QPushButton("Check")
        check_btn.setObjectName("Primary")
        check_btn.clicked.connect(self._on_stage2_submit)
        layout.addWidget(check_btn)

        self.stage2_feedback = QLabel("")
        self.stage2_feedback.setObjectName("CardBack")
        self.stage2_feedback.setWordWrap(True)
        self.stage2_feedback.hide()
        layout.addWidget(self.stage2_feedback)

        feedback_row = QHBoxLayout()
        self.got_it_right_btn = QPushButton("I got it right")
        self.got_it_right_btn.setObjectName("Secondary")
        self.got_it_right_btn.clicked.connect(self._on_got_it_right)
        self.got_it_right_btn.hide()
        feedback_row.addWidget(self.got_it_right_btn)

        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setObjectName("Primary")
        self.continue_btn.clicked.connect(self._on_stage2_continue)
        self.continue_btn.hide()
        feedback_row.addWidget(self.continue_btn)
        layout.addLayout(feedback_row)

        layout.addStretch()
        return page

    def _build_done_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        done_label = QLabel("You've mastered every card in this deck!")
        done_label.setObjectName("CardFront")
        done_label.setWordWrap(True)
        layout.addWidget(done_label)

        reset_btn = QPushButton("Reset & Practice Again")
        reset_btn.setObjectName("Primary")
        reset_btn.clicked.connect(self._reset_progress)
        layout.addWidget(reset_btn)
        layout.addStretch()
        return page

    # -- session lifecycle ------------------------------------------------

    def start(self, deck_id: int) -> None:
        with db_session() as conn:
            self.deck = deck_repository.get_deck(conn, deck_id)
            self.all_cards = card_repository.list_cards(conn, deck_id)
            progress = learn_repository.get_progress_map(conn, deck_id)

        self.title_label.setText(f"{self.deck.name} — Learn")
        self._locked = False
        self._answered_count = 0

        if len(self.all_cards) < MIN_CARDS:
            self.message_label.setText(f"Learn needs at least {MIN_CARDS} cards in this deck.")
            self.progress_label.setText("")
            for btn in self.stage1_buttons:
                btn.hide()
            self.stage1_prompt.setText("")
            return
        for btn in self.stage1_buttons:
            btn.show()

        self.message_label.setText("")
        by_id = {c.id: c for c in self.all_cards}
        self.stage1_queue = [c for c in self.all_cards if progress.get(c.id, "stage1") == "stage1"]
        self.stage2_queue = [by_id[cid] for cid, stage in progress.items() if stage == "stage2"]
        self.mastered_count = sum(1 for stage in progress.values() if stage == "mastered")

        self._load_next()

    def _update_progress_label(self) -> None:
        self.progress_label.setText(f"{self.mastered_count} of {len(self.all_cards)} mastered")

    def _load_next(self) -> None:
        self._update_progress_label()
        self.stage2_feedback.hide()
        self.got_it_right_btn.hide()
        self.continue_btn.hide()
        self.stage2_input.setEnabled(True)
        self.stage2_input.clear()
        self._locked = False

        if self.stage1_queue:
            self.current_card = self.stage1_queue.pop(0)
            self._show_stage1(self.current_card)
        elif self.stage2_queue:
            self.current_card = self.stage2_queue.pop(0)
            self._show_stage2(self.current_card)
        else:
            self.current_card = None
            self.pages.setCurrentIndex(2)

    def _show_stage1(self, card) -> None:
        self.pages.setCurrentIndex(0)
        prompt = prompt_text(card, self.deck.back_fields) or (card.back or "")
        self.stage1_prompt.setText(prompt)

        correct = prompt_text(card, self.deck.front_fields) or card.front
        distractors = pick_distractors(self.all_cards, card, self.deck.front_fields, count=3)
        options = [correct] + distractors
        random.shuffle(options)

        for btn, text in zip(self.stage1_buttons, options):
            btn.setText(text)
            btn.setProperty("isCorrect", text == correct)
            btn.setEnabled(True)
            btn.setObjectName("Secondary")
            btn.setStyleSheet("")

    def _show_stage2(self, card) -> None:
        self.pages.setCurrentIndex(1)
        prompt = prompt_text(card, self.deck.back_fields) or (card.back or "")
        self.stage2_prompt.setText(prompt)
        self.stage2_input.setFocus()

    # -- stage 1 handling --------------------------------------------------

    def _on_stage1_answer(self, button: QPushButton) -> None:
        if self._locked or self.current_card is None:
            return
        self._locked = True
        self._answered_count += 1
        card = self.current_card
        is_correct = bool(button.property("isCorrect"))

        for btn in self.stage1_buttons:
            btn.setEnabled(False)
            if bool(btn.property("isCorrect")):
                btn.setStyleSheet("background-color: #3ec98a; color: #1b1e27;")
            elif btn is button:
                btn.setStyleSheet("background-color: #e5566d; color: #ffffff;")

        with db_session() as conn:
            if is_correct:
                learn_repository.set_stage(conn, self.deck.id, card.id, "stage2")
            else:
                learn_repository.set_stage(conn, self.deck.id, card.id, "stage1")

        if is_correct:
            self.stage2_queue.append(card)
        else:
            self.stage1_queue.append(card)

        QTimer.singleShot(WRONG_ANSWER_PAUSE_MS if not is_correct else 350, self._load_next)

    # -- stage 2 handling --------------------------------------------------

    def _on_stage2_submit(self) -> None:
        if self._locked or self.current_card is None:
            return
        self._answered_count += 1
        card = self.current_card
        user_text = self.stage2_input.text()
        correct_text = prompt_text(card, self.deck.front_fields) or card.front

        if fuzzy_match(user_text, correct_text):
            self._locked = True
            self.mastered_count += 1
            with db_session() as conn:
                learn_repository.set_stage(conn, self.deck.id, card.id, "mastered")
            QTimer.singleShot(300, self._load_next)
            return

        self._locked = True
        self.stage2_input.setEnabled(False)
        self.stage2_feedback.setText(f"Correct answer: {correct_text}")
        self.stage2_feedback.show()
        self.got_it_right_btn.show()
        self.continue_btn.show()

    def _on_got_it_right(self) -> None:
        if self.current_card is None:
            return
        card = self.current_card
        self.mastered_count += 1
        with db_session() as conn:
            learn_repository.set_stage(conn, self.deck.id, card.id, "mastered")
        self._load_next()

    def _on_stage2_continue(self) -> None:
        if self.current_card is None:
            return
        card = self.current_card
        with db_session() as conn:
            learn_repository.set_stage(conn, self.deck.id, card.id, "stage1")
        self.stage1_queue.append(card)
        self._load_next()

    def _reset_progress(self) -> None:
        if self.deck is None:
            return
        with db_session() as conn:
            learn_repository.reset_progress(conn, self.deck.id)
        self.start(self.deck.id)

    def _leave(self) -> None:
        if self.deck is not None and self._answered_count > 0:
            summary = f"{self.mastered_count} of {len(self.all_cards)} mastered"
            with db_session() as conn:
                history_repository.log_session(conn, self.deck.id, "learn", summary)
        self.back_requested.emit()
