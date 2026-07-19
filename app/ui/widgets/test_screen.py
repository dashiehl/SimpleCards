from __future__ import annotations

import random

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QScrollArea, QSpinBox, QStackedLayout, QVBoxLayout, QWidget,
)

from app.db import card_repository, deck_repository, history_repository
from app.db.connection import db_session
from app.study_modes.practice import fuzzy_match, pick_distractors, prompt_text

MIN_CARDS = 2
MIN_CARDS_FOR_CHOICE = 4
MAX_MATCHING_ROWS = 5


class TestScreen(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.deck = None
        self.all_cards: list = []
        self._questions: list[dict] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(16)

        top_row = QHBoxLayout()
        back_btn = QPushButton("< Study Options")
        back_btn.setObjectName("Secondary")
        back_btn.clicked.connect(self.back_requested.emit)
        top_row.addWidget(back_btn)
        self.title_label = QLabel("Test")
        self.title_label.setObjectName("AppTitle")
        top_row.addWidget(self.title_label)
        top_row.addStretch()
        outer.addLayout(top_row)

        self.pages = QStackedLayout()
        outer.addLayout(self.pages, stretch=1)

        self.pages.addWidget(self._build_setup_page())
        self.pages.addWidget(self._build_running_page())
        self.pages.addWidget(self._build_results_page())

    # -- setup -------------------------------------------------------------

    def _build_setup_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        self.setup_message = QLabel("")
        self.setup_message.setObjectName("DeckMeta")
        self.setup_message.setWordWrap(True)
        layout.addWidget(self.setup_message)

        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("Number of questions"))
        self.count_spin = QSpinBox()
        self.count_spin.setMinimum(1)
        count_row.addWidget(self.count_spin)
        count_row.addStretch()
        layout.addLayout(count_row)

        layout.addWidget(QLabel("Question types"))
        self.mc_check = QCheckBox("Multiple choice")
        self.tf_check = QCheckBox("True / False")
        self.written_check = QCheckBox("Written")
        self.matching_check = QCheckBox("Matching")
        for cb in (self.mc_check, self.tf_check, self.written_check, self.matching_check):
            cb.setChecked(True)
            layout.addWidget(cb)

        start_btn = QPushButton("Start Test")
        start_btn.setObjectName("Primary")
        start_btn.clicked.connect(self._begin_test)
        layout.addWidget(start_btn)

        layout.addStretch()
        return page

    # -- running -------------------------------------------------------------

    def _build_running_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.questions_container = QWidget()
        self.questions_layout = QVBoxLayout(self.questions_container)
        self.questions_layout.setSpacing(14)
        scroll.setWidget(self.questions_container)
        layout.addWidget(scroll, stretch=1)

        submit_btn = QPushButton("Submit Test")
        submit_btn.setObjectName("Primary")
        submit_btn.clicked.connect(self._submit_test)
        layout.addWidget(submit_btn)
        return page

    # -- results -------------------------------------------------------------

    def _build_results_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.score_label = QLabel("")
        self.score_label.setObjectName("CardFront")
        layout.addWidget(self.score_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(10)
        scroll.setWidget(self.results_container)
        layout.addWidget(scroll, stretch=1)

        button_row = QHBoxLayout()
        retake_btn = QPushButton("Retake")
        retake_btn.setObjectName("Primary")
        retake_btn.clicked.connect(self._begin_test)
        button_row.addWidget(retake_btn)
        button_row.addStretch()
        layout.addLayout(button_row)
        return page

    # -- lifecycle -------------------------------------------------------------

    def start(self, deck_id: int) -> None:
        with db_session() as conn:
            self.deck = deck_repository.get_deck(conn, deck_id)
            self.all_cards = card_repository.list_cards(conn, deck_id)

        self.title_label.setText(f"{self.deck.name} — Test")
        total = len(self.all_cards)

        can_choice = total >= MIN_CARDS_FOR_CHOICE
        self.mc_check.setEnabled(can_choice)
        self.tf_check.setEnabled(can_choice)
        self.mc_check.setChecked(can_choice)
        self.tf_check.setChecked(can_choice)

        if total < MIN_CARDS:
            self.setup_message.setText(f"Test needs at least {MIN_CARDS} cards in this deck.")
            self.count_spin.setEnabled(False)
            for cb in (self.mc_check, self.tf_check, self.written_check, self.matching_check):
                cb.setEnabled(False)
        else:
            note = "" if can_choice else f" (Multiple choice and True/False need at least {MIN_CARDS_FOR_CHOICE} cards.)"
            self.setup_message.setText(f"This deck has {total} cards.{note}")
            self.count_spin.setEnabled(True)
            self.count_spin.setMaximum(total)
            self.count_spin.setValue(min(10, total))

        self.pages.setCurrentIndex(0)

    def _begin_test(self) -> None:
        if len(self.all_cards) < MIN_CARDS:
            return

        enabled_types = []
        if self.mc_check.isChecked() and self.mc_check.isEnabled():
            enabled_types.append("mc")
        if self.tf_check.isChecked() and self.tf_check.isEnabled():
            enabled_types.append("tf")
        if self.written_check.isChecked():
            enabled_types.append("written")
        use_matching = self.matching_check.isChecked() and len(self.all_cards) >= MIN_CARDS

        if not enabled_types and not use_matching:
            self.setup_message.setText("Choose at least one question type.")
            return

        n = min(self.count_spin.value(), len(self.all_cards))
        sample = random.sample(self.all_cards, n)

        self._questions = []
        remaining = list(sample)

        if use_matching:
            if enabled_types:
                # Leave room for the other checked types instead of letting Matching
                # consume the whole sample when the question count is small.
                matching_size = min(MAX_MATCHING_ROWS, max(2, n // 2), len(remaining))
            else:
                matching_size = min(MAX_MATCHING_ROWS, len(remaining))
            matching_cards = remaining[:matching_size]
            remaining = remaining[matching_size:]
            if matching_cards:
                self._questions.append(self._make_matching_question(matching_cards))

        if enabled_types:
            for i, card in enumerate(remaining):
                q_type = enabled_types[i % len(enabled_types)]
                if q_type == "mc":
                    self._questions.append(self._make_mc_question(card))
                elif q_type == "tf":
                    self._questions.append(self._make_tf_question(card))
                else:
                    self._questions.append(self._make_written_question(card))

        random.shuffle(self._questions)
        self._render_questions()
        self.pages.setCurrentIndex(1)

    # -- question builders -------------------------------------------------------------

    def _make_mc_question(self, card) -> dict:
        prompt = prompt_text(card, self.deck.back_fields) or (card.back or "")
        correct = prompt_text(card, self.deck.front_fields) or card.front
        distractors = pick_distractors(self.all_cards, card, self.deck.front_fields, count=3)
        options = [correct] + distractors
        random.shuffle(options)
        return {"type": "mc", "prompt": prompt, "options": options, "correct": correct}

    def _make_tf_question(self, card) -> dict:
        front_text = prompt_text(card, self.deck.front_fields) or card.front
        is_true = random.random() < 0.5
        if is_true:
            back_text = prompt_text(card, self.deck.back_fields) or (card.back or "")
        else:
            others = [c for c in self.all_cards if c.id != card.id]
            other = random.choice(others)
            back_text = prompt_text(other, self.deck.back_fields) or (other.back or "")
        return {"type": "tf", "front": front_text, "back": back_text, "correct": is_true}

    def _make_written_question(self, card) -> dict:
        prompt = prompt_text(card, self.deck.back_fields) or (card.back or "")
        correct = prompt_text(card, self.deck.front_fields) or card.front
        return {"type": "written", "prompt": prompt, "correct": correct}

    def _make_matching_question(self, cards: list) -> dict:
        options = [prompt_text(c, self.deck.front_fields) or c.front for c in cards]
        rows = []
        for card in cards:
            back_text = prompt_text(card, self.deck.back_fields) or (card.back or "")
            correct = prompt_text(card, self.deck.front_fields) or card.front
            rows.append({"back_text": back_text, "correct": correct})
        return {"type": "matching", "rows": rows, "options": options}

    # -- rendering -------------------------------------------------------------

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _render_questions(self) -> None:
        self._clear_layout(self.questions_layout)

        for i, q in enumerate(self._questions, start=1):
            box = QGroupBox(f"Question {i}")
            box_layout = QVBoxLayout(box)

            if q["type"] == "mc":
                label = QLabel(q["prompt"])
                label.setWordWrap(True)
                box_layout.addWidget(label)
                group = QButtonGroup(box)
                buttons = []
                for option in q["options"]:
                    radio = QRadioButton(option)
                    group.addButton(radio)
                    box_layout.addWidget(radio)
                    buttons.append(radio)
                q["group"] = group
                q["buttons"] = buttons

            elif q["type"] == "tf":
                label = QLabel(f'"{q["front"]}" means "{q["back"]}"')
                label.setWordWrap(True)
                box_layout.addWidget(label)
                group = QButtonGroup(box)
                true_btn = QRadioButton("True")
                false_btn = QRadioButton("False")
                group.addButton(true_btn)
                group.addButton(false_btn)
                box_layout.addWidget(true_btn)
                box_layout.addWidget(false_btn)
                q["group"] = group
                q["true_btn"] = true_btn
                q["false_btn"] = false_btn

            elif q["type"] == "written":
                label = QLabel(q["prompt"])
                label.setWordWrap(True)
                box_layout.addWidget(label)
                line_edit = QLineEdit()
                line_edit.setPlaceholderText("Type the answer...")
                box_layout.addWidget(line_edit)
                q["input"] = line_edit

            else:  # matching
                combos = []
                for row in q["rows"]:
                    row_layout = QHBoxLayout()
                    back_label = QLabel(row["back_text"])
                    back_label.setWordWrap(True)
                    row_layout.addWidget(back_label, stretch=1)
                    combo = QComboBox()
                    combo.addItem("")
                    combo.addItems(q["options"])
                    row_layout.addWidget(combo)
                    box_layout.addLayout(row_layout)
                    combos.append(combo)
                q["combos"] = combos

            self.questions_layout.addWidget(box)
        self.questions_layout.addStretch()

    def _submit_test(self) -> None:
        correct_count = 0
        total_count = 0
        self._clear_layout(self.results_layout)

        for i, q in enumerate(self._questions, start=1):
            if q["type"] == "matching":
                for row, combo in zip(q["rows"], q["combos"]):
                    total_count += 1
                    is_correct = combo.currentText() == row["correct"]
                    correct_count += int(is_correct)
                    self._add_result_row(i, is_correct, row["back_text"], row["correct"], combo.currentText())
                continue

            total_count += 1
            if q["type"] == "mc":
                checked = next((b.text() for b in q["buttons"] if b.isChecked()), "")
                is_correct = checked == q["correct"]
                self._add_result_row(i, is_correct, q["prompt"], q["correct"], checked)
            elif q["type"] == "tf":
                if q["true_btn"].isChecked():
                    given = True
                elif q["false_btn"].isChecked():
                    given = False
                else:
                    given = None
                is_correct = given == q["correct"]
                given_text = "True" if given is True else ("False" if given is False else "(no answer)")
                correct_text = "True" if q["correct"] else "False"
                self._add_result_row(i, is_correct, f'"{q["front"]}" means "{q["back"]}"', correct_text, given_text)
            else:  # written
                given = q["input"].text()
                is_correct = fuzzy_match(given, q["correct"])
                self._add_result_row(i, is_correct, q["prompt"], q["correct"], given)

            correct_count += int(is_correct)

        self.results_layout.addStretch()
        self.score_label.setText(f"{correct_count} / {total_count} correct")
        self.pages.setCurrentIndex(2)

        with db_session() as conn:
            history_repository.log_session(
                conn, self.deck.id, "test", f"{correct_count} / {total_count} correct",
            )

    def _add_result_row(self, number: int, is_correct: bool, prompt: str, correct: str, given: str) -> None:
        mark = "✓" if is_correct else "✗"
        text = f"{mark} Q{number}: {prompt}"
        if not is_correct:
            text += f"\n    Your answer: {given or '(no answer)'} — Correct answer: {correct}"
        label = QLabel(text)
        label.setObjectName("CardBack" if is_correct else "CardExample")
        label.setWordWrap(True)
        self.results_layout.addWidget(label)
