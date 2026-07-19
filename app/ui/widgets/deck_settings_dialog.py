from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout,
)

from app.db import card_repository, deck_repository
from app.db.connection import db_session
from app.db.field_layout import label_for


class DeckSettingsDialog(QDialog):
    """Lets the user choose which fields appear on the front vs. back of a card."""

    def __init__(self, deck_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Deck Settings")
        self.setMinimumSize(560, 420)

        with db_session() as conn:
            self.deck = deck_repository.get_deck(conn, deck_id)
            available = card_repository.field_keys_in_use(conn, deck_id)

        used = set(self.deck.front_fields) | set(self.deck.back_fields)
        unused = [k for k in available if k not in used]
        self.deleted = False

        layout = QVBoxLayout(self)
        title_row = QHBoxLayout()
        title = QLabel(f'Card layout for "{self.deck.name}"')
        title.setObjectName("DeckName")
        title_row.addWidget(title)
        title_row.addStretch()
        delete_btn = QPushButton("Delete Deck")
        delete_btn.setObjectName("Destructive")
        delete_btn.clicked.connect(self._delete_deck)
        title_row.addWidget(delete_btn)
        layout.addLayout(title_row)
        hint = QLabel("Choose what shows on the front vs. the back of each card. Move fields between columns.")
        hint.setObjectName("DeckMeta")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        columns = QHBoxLayout()

        avail_box = QGroupBox("Unused fields")
        avail_layout = QVBoxLayout(avail_box)
        self.available_list = QListWidget()
        for key in unused:
            self._add_item(self.available_list, key)
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
        for key in self.deck.front_fields:
            self._add_item(self.front_list, key)
        front_layout.addWidget(self.front_list)
        columns.addWidget(front_box)

        back_box = QGroupBox("Back of card")
        back_layout = QVBoxLayout(back_box)
        self.back_list = QListWidget()
        for key in self.deck.back_fields:
            self._add_item(self.back_list, key)
        back_layout.addWidget(self.back_list)
        columns.addWidget(back_box)

        layout.addLayout(columns)

        to_front_btn.clicked.connect(lambda: self._move_selected(self.front_list))
        to_back_btn.clicked.connect(lambda: self._move_selected(self.back_list))
        to_unused_btn.clicked.connect(lambda: self._move_selected(self.available_list))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _add_item(list_widget: QListWidget, key: str) -> None:
        item = QListWidgetItem(label_for(key))
        item.setData(1000, key)
        list_widget.addItem(item)

    def _move_selected(self, target: QListWidget) -> None:
        for source in (self.available_list, self.front_list, self.back_list):
            if source is target:
                continue
            for item in source.selectedItems():
                source.takeItem(source.row(item))
                self._add_item(target, item.data(1000))

    @staticmethod
    def _keys(list_widget: QListWidget) -> list[str]:
        return [list_widget.item(i).data(1000) for i in range(list_widget.count())]

    def save(self) -> None:
        with db_session() as conn:
            deck_repository.set_field_layout(conn, self.deck.id, self._keys(self.front_list), self._keys(self.back_list))

    def _delete_deck(self) -> None:
        answer = QMessageBox.question(
            self, "Delete deck",
            f'Delete "{self.deck.name}" and all of its cards? This cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        with db_session() as conn:
            deck_repository.delete_deck(conn, self.deck.id)

        self.deleted = True
        self.reject()
