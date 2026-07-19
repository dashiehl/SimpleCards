from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.db import card_repository, deck_repository
from app.db.connection import db_session
from app.ui.widgets.card_editor_dialog import CardEditorDialog

ALL_TAGS = "All tags"


class CardBrowser(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.deck_id: int | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(14)

        top_row = QHBoxLayout()
        back_btn = QPushButton("< Decks")
        back_btn.setObjectName("Secondary")
        back_btn.clicked.connect(self.back_requested.emit)
        top_row.addWidget(back_btn)
        self.title_label = QLabel("")
        self.title_label.setObjectName("AppTitle")
        top_row.addWidget(self.title_label)
        top_row.addStretch()
        add_btn = QPushButton("+ Add Card")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_card)
        top_row.addWidget(add_btn)
        outer.addLayout(top_row)

        filter_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search front, back, or any field...")
        self.search_edit.textChanged.connect(self.refresh)
        filter_row.addWidget(self.search_edit)
        self.tag_combo = QComboBox()
        self.tag_combo.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.tag_combo)
        outer.addLayout(filter_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Front", "Back", "Tags", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 130)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        outer.addWidget(self.table, stretch=1)

        self.count_label = QLabel("")
        self.count_label.setObjectName("DeckMeta")
        outer.addWidget(self.count_label)

    def open_deck(self, deck_id: int) -> None:
        self.deck_id = deck_id
        with db_session() as conn:
            deck = deck_repository.get_deck(conn, deck_id)
        self.title_label.setText(deck.name)
        self._refresh_tag_filter()
        self.refresh()

    def _refresh_tag_filter(self) -> None:
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem(ALL_TAGS)
        with db_session() as conn:
            for tag in card_repository.all_tags(conn, self.deck_id):
                self.tag_combo.addItem(tag)
        self.tag_combo.blockSignals(False)

    def refresh(self) -> None:
        if self.deck_id is None:
            return
        query = self.search_edit.text().strip()
        tag = self.tag_combo.currentText()
        tag = None if tag in ("", ALL_TAGS) else tag

        with db_session() as conn:
            cards = card_repository.search_cards(conn, self.deck_id, query=query, tag=tag)

        self.table.setRowCount(len(cards))
        for row, card in enumerate(cards):
            self.table.setItem(row, 0, QTableWidgetItem(card.front))
            self.table.setItem(row, 1, QTableWidgetItem(card.back or ""))
            self.table.setItem(row, 2, QTableWidgetItem(", ".join(card.tags)))

            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            edit_btn = QPushButton("Edit")
            edit_btn.setObjectName("TableAction")
            edit_btn.clicked.connect(lambda _, c=card: self._edit_card(c))
            delete_btn = QPushButton("Delete")
            delete_btn.setObjectName("TableAction")
            delete_btn.clicked.connect(lambda _, c=card: self._delete_card(c))
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.table.setCellWidget(row, 3, actions)

        self.count_label.setText(f"{len(cards)} card(s)")

    def _add_card(self) -> None:
        dialog = CardEditorDialog(parent=self)
        if dialog.exec():
            card = dialog.result_card(self.deck_id)
            with db_session() as conn:
                card_repository.create_card(
                    conn, deck_id=self.deck_id, front=card.front, back=card.back, kind=card.kind,
                    extra_fields=card.extra_fields, tags=card.tags,
                )
            self._refresh_tag_filter()
            self.refresh()

    def _edit_card(self, card) -> None:
        dialog = CardEditorDialog(card=card, parent=self)
        if dialog.exec():
            updated = dialog.result_card(self.deck_id)
            with db_session() as conn:
                card_repository.update_card(conn, updated)
            self._refresh_tag_filter()
            self.refresh()

    def _delete_card(self, card) -> None:
        confirm = QMessageBox.question(self, "Delete card", f'Delete "{card.front}"?')
        if confirm == QMessageBox.StandardButton.Yes:
            with db_session() as conn:
                card_repository.delete_card(conn, card.id)
            self.refresh()
