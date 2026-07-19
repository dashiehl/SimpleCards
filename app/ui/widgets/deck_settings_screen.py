from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from app.db import card_repository, deck_repository
from app.db.connection import db_session
from app.db.field_layout import label_for

FIELD_ROLE = 1000


class DeckSettingsScreen(QWidget):
    """Lets the user rename a deck, choose which fields appear on the front vs. back of a card, or delete it."""

    back_requested = Signal()
    deck_deleted = Signal()

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
        title = QLabel("Deck Settings")
        title.setObjectName("AppTitle")
        top_row.addWidget(title)
        top_row.addStretch()
        delete_btn = QPushButton("Delete Deck")
        delete_btn.setObjectName("Destructive")
        delete_btn.clicked.connect(self._delete_deck)
        top_row.addWidget(delete_btn)
        outer.addLayout(top_row)

        rename_row = QHBoxLayout()
        rename_row.addWidget(QLabel("Name"))
        self.name_edit = QLineEdit()
        rename_row.addWidget(self.name_edit, stretch=1)
        rename_btn = QPushButton("Rename")
        rename_btn.setObjectName("Secondary")
        rename_btn.clicked.connect(self._rename_deck)
        rename_row.addWidget(rename_btn)
        outer.addLayout(rename_row)

        hint = QLabel("Choose what shows on the front vs. the back of each card. Move fields between columns.")
        hint.setObjectName("DeckMeta")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        columns = QHBoxLayout()

        avail_box = QGroupBox("Unused fields")
        avail_layout = QVBoxLayout(avail_box)
        self.available_list = QListWidget()
        avail_layout.addWidget(self.available_list)
        columns.addWidget(avail_box)

        mid_buttons = QVBoxLayout()
        to_front_btn = QPushButton("-> Front")
        to_back_btn = QPushButton("-> Back")
        to_unused_btn = QPushButton("<- Remove")
        for btn in (to_front_btn, to_back_btn, to_unused_btn):
            btn.setObjectName("Secondary")
        mid_buttons.addStretch()
        mid_buttons.addWidget(to_front_btn)
        mid_buttons.addWidget(to_back_btn)
        mid_buttons.addWidget(to_unused_btn)
        mid_buttons.addStretch()
        columns.addLayout(mid_buttons)

        front_box = QGroupBox("Front of card")
        front_layout = QVBoxLayout(front_box)
        self.front_list = QListWidget()
        front_layout.addWidget(self.front_list)
        columns.addWidget(front_box)

        back_box = QGroupBox("Back of card")
        back_layout = QVBoxLayout(back_box)
        self.back_list = QListWidget()
        back_layout.addWidget(self.back_list)
        columns.addWidget(back_box)

        outer.addLayout(columns, stretch=1)

        to_front_btn.clicked.connect(lambda: self._move_selected(self.front_list))
        to_back_btn.clicked.connect(lambda: self._move_selected(self.back_list))
        to_unused_btn.clicked.connect(lambda: self._move_selected(self.available_list))

        save_row = QHBoxLayout()
        save_row.addStretch()
        save_btn = QPushButton("Save Layout")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save_layout)
        save_row.addWidget(save_btn)
        outer.addLayout(save_row)

    def open_deck(self, deck_id: int) -> None:
        self.deck_id = deck_id
        with db_session() as conn:
            deck = deck_repository.get_deck(conn, deck_id)
            available = card_repository.field_keys_in_use(conn, deck_id)

        self.name_edit.setText(deck.name)

        used = set(deck.front_fields) | set(deck.back_fields)
        unused = [k for k in available if k not in used]

        self.available_list.clear()
        self.front_list.clear()
        self.back_list.clear()
        for key in unused:
            self._add_item(self.available_list, key)
        for key in deck.front_fields:
            self._add_item(self.front_list, key)
        for key in deck.back_fields:
            self._add_item(self.back_list, key)

    @staticmethod
    def _add_item(list_widget: QListWidget, key: str) -> None:
        item = QListWidgetItem(label_for(key))
        item.setData(FIELD_ROLE, key)
        list_widget.addItem(item)

    def _move_selected(self, target: QListWidget) -> None:
        for source in (self.available_list, self.front_list, self.back_list):
            if source is target:
                continue
            for item in source.selectedItems():
                source.takeItem(source.row(item))
                self._add_item(target, item.data(FIELD_ROLE))

    @staticmethod
    def _keys(list_widget: QListWidget) -> list[str]:
        return [list_widget.item(i).data(FIELD_ROLE) for i in range(list_widget.count())]

    def _save_layout(self) -> None:
        with db_session() as conn:
            deck_repository.set_field_layout(conn, self.deck_id, self._keys(self.front_list), self._keys(self.back_list))
        QMessageBox.information(self, "Saved", "Card layout saved.")

    def _rename_deck(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Name required", "Give the deck a name first.")
            return
        with db_session() as conn:
            deck_repository.rename_deck(conn, self.deck_id, name)

    def _delete_deck(self) -> None:
        with db_session() as conn:
            deck = deck_repository.get_deck(conn, self.deck_id)
        answer = QMessageBox.question(
            self, "Delete deck",
            f'Delete "{deck.name}" and all of its cards? This cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        with db_session() as conn:
            deck_repository.delete_deck(conn, self.deck_id)

        self.deck_deleted.emit()
