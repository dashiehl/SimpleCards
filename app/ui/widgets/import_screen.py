from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.db import deck_repository
from app.db.connection import db_session
from app.db.field_layout import label_for, suggest_layout
from app.pdf_import.import_pdf import commit_candidates_to_deck, commit_candidates_to_new_deck
from app.pdf_import.import_pdf import extract_candidates as run_extraction

NEW_DECK_SENTINEL = "__new_deck__"

CARD_TYPE_MODES = [
    ("Auto-detect", "auto"),
    ("Simple (Front / Back)", "simple"),
    ("Detailed (multi-field)", "detailed"),
]

FIELD_ROLE = 1000


class ImportScreen(QWidget):
    imported = Signal(int)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.candidates = []
        self.pdf_path = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(14)

        header = QLabel("Import from PDF")
        header.setObjectName("AppTitle")
        outer.addWidget(header)

        subtitle = QLabel(
            "Runs fully on your computer — no internet connection or API key required. "
            "Pick a PDF, review the auto-detected cards below, edit anything that's off, then import."
        )
        subtitle.setObjectName("DeckMeta")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        picker_row = QHBoxLayout()
        choose_btn = QPushButton("Choose PDF...")
        choose_btn.setObjectName("Secondary")
        choose_btn.clicked.connect(self._choose_pdf)
        picker_row.addWidget(choose_btn)
        self.file_label = QLabel("No file selected")
        self.file_label.setObjectName("DeckMeta")
        picker_row.addWidget(self.file_label)
        picker_row.addStretch()
        picker_row.addWidget(QLabel("Card type:"))
        self.card_type_combo = QComboBox()
        for label, _mode in CARD_TYPE_MODES:
            self.card_type_combo.addItem(label)
        self.card_type_combo.currentIndexChanged.connect(self._on_card_type_changed)
        picker_row.addWidget(self.card_type_combo)
        outer.addLayout(picker_row)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Import into:"))
        self.deck_combo = QComboBox()
        self.deck_combo.currentIndexChanged.connect(self._on_deck_selection_changed)
        target_row.addWidget(self.deck_combo)
        self.new_deck_name = QLineEdit()
        self.new_deck_name.setPlaceholderText("New deck name")
        target_row.addWidget(self.new_deck_name)
        target_row.addStretch()
        outer.addLayout(target_row)

        outer.addWidget(self._build_field_layout_box())

        self.extra_field_keys: list[str] = []
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Include", "Front", "Back", "Confidence"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self._update_count_label)
        outer.addWidget(self.table, stretch=1)

        bottom_row = QHBoxLayout()
        self.count_label = QLabel("")
        self.count_label.setObjectName("DeckMeta")
        bottom_row.addWidget(self.count_label)
        bottom_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("Secondary")
        cancel_btn.clicked.connect(self._cancel)
        bottom_row.addWidget(cancel_btn)
        self.import_btn = QPushButton("Import Selected")
        self.import_btn.setObjectName("Primary")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._commit)
        bottom_row.addWidget(self.import_btn)
        outer.addLayout(bottom_row)

        self.refresh_decks()

    def _build_field_layout_box(self) -> QGroupBox:
        box = QGroupBox("Card fields")
        layout = QVBoxLayout(box)
        hint = QLabel("Choose which detected fields show on the front vs. the back of each card.")
        hint.setObjectName("DeckMeta")
        hint.setWordWrap(True)
        layout.addWidget(hint)

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

        layout.addLayout(columns)

        to_front_btn.clicked.connect(lambda: self._move_selected(self.front_list))
        to_back_btn.clicked.connect(lambda: self._move_selected(self.back_list))
        to_unused_btn.clicked.connect(lambda: self._move_selected(self.available_list))

        return box

    @staticmethod
    def _add_field_item(list_widget: QListWidget, key: str) -> None:
        item = QListWidgetItem(label_for(key))
        item.setData(FIELD_ROLE, key)
        list_widget.addItem(item)

    def _move_selected(self, target: QListWidget) -> None:
        for source in (self.available_list, self.front_list, self.back_list):
            if source is target:
                continue
            for item in source.selectedItems():
                source.takeItem(source.row(item))
                self._add_field_item(target, item.data(FIELD_ROLE))

    @staticmethod
    def _keys(list_widget: QListWidget) -> list[str]:
        return [list_widget.item(i).data(FIELD_ROLE) for i in range(list_widget.count())]

    def _populate_field_layout(self) -> None:
        available_keys: list[str] = []
        for c in self.candidates:
            if "front" not in available_keys:
                available_keys.append("front")
            if c.back and "back" not in available_keys:
                available_keys.append("back")
            for key in c.extra_fields:
                if key not in available_keys:
                    available_keys.append(key)

        front, back = suggest_layout(available_keys)
        unused = [k for k in available_keys if k not in front and k not in back]

        self.available_list.clear()
        self.front_list.clear()
        self.back_list.clear()
        for key in unused:
            self._add_field_item(self.available_list, key)
        for key in front:
            self._add_field_item(self.front_list, key)
        for key in back:
            self._add_field_item(self.back_list, key)

    def refresh_decks(self) -> None:
        self.deck_combo.blockSignals(True)
        self.deck_combo.clear()
        self.deck_combo.addItem("+ New deck", NEW_DECK_SENTINEL)
        with db_session() as conn:
            for deck in deck_repository.list_decks(conn):
                self.deck_combo.addItem(deck.name, deck.id)
        self.deck_combo.blockSignals(False)
        self._on_deck_selection_changed()

    def _on_deck_selection_changed(self) -> None:
        is_new = self.deck_combo.currentData() == NEW_DECK_SENTINEL
        self.new_deck_name.setVisible(is_new)

    def _current_mode(self) -> str:
        return CARD_TYPE_MODES[self.card_type_combo.currentIndex()][1]

    def _on_card_type_changed(self) -> None:
        if not self.pdf_path:
            return
        self.candidates = run_extraction(self.pdf_path, mode=self._current_mode())
        self._populate_table()

    def _choose_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose a PDF", "", "PDF files (*.pdf)")
        if not path:
            return
        self.pdf_path = path
        self.file_label.setText(path.split("/")[-1].split("\\")[-1])
        self.candidates = run_extraction(path, mode=self._current_mode())
        if self.new_deck_name.text().strip() == "":
            stem = path.split("/")[-1].split("\\")[-1].rsplit(".", 1)[0]
            self.new_deck_name.setText(stem.replace("_", " ").title())
        self._populate_table()

    def _populate_table(self) -> None:
        self._populate_field_layout()

        extra_keys: list[str] = []
        for c in self.candidates:
            for key in c.extra_fields:
                if key not in extra_keys:
                    extra_keys.append(key)
        self.extra_field_keys = extra_keys

        headers = ["Include", "Front", "Back"] + [label_for(k) for k in extra_keys] + ["Confidence"]
        conf_col = len(headers) - 1

        self.table.blockSignals(True)
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setRowCount(len(self.candidates))
        for row, c in enumerate(self.candidates):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            check_item.setCheckState(Qt.CheckState.Checked if c.include else Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, check_item)

            front_item = QTableWidgetItem(c.front)
            back_item = QTableWidgetItem(c.back or "")
            self.table.setItem(row, 1, front_item)
            self.table.setItem(row, 2, back_item)

            for col_offset, key in enumerate(extra_keys):
                extra_item = QTableWidgetItem(c.extra_fields.get(key, ""))
                self.table.setItem(row, 3 + col_offset, extra_item)

            conf_item = QTableWidgetItem(f"{c.confidence:.1f}")
            conf_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            if c.confidence < 0.6:
                conf_item.setForeground(Qt.GlobalColor.yellow)
            self.table.setItem(row, conf_col, conf_item)
        self.table.blockSignals(False)
        self._update_count_label()

    def _update_count_label(self) -> None:
        selected = sum(
            1 for row in range(self.table.rowCount())
            if self.table.item(row, 0) and self.table.item(row, 0).checkState() == Qt.CheckState.Checked
        )
        self.count_label.setText(f"{selected} of {len(self.candidates)} cards will be imported")
        self.import_btn.setEnabled(selected > 0)

    def _commit(self) -> None:
        for row, c in enumerate(self.candidates):
            check_item = self.table.item(row, 0)
            c.include = check_item.checkState() == Qt.CheckState.Checked
            c.front = self.table.item(row, 1).text().strip()
            c.back = self.table.item(row, 2).text().strip()
            for col_offset, key in enumerate(self.extra_field_keys):
                value = self.table.item(row, 3 + col_offset).text().strip()
                if value:
                    c.extra_fields[key] = value
                else:
                    c.extra_fields.pop(key, None)

        front_fields = self._keys(self.front_list)
        back_fields = self._keys(self.back_list)
        if not front_fields:
            QMessageBox.warning(self, "Front field required", "Choose at least one field for the front of the card.")
            return

        target = self.deck_combo.currentData()
        with db_session() as conn:
            if target == NEW_DECK_SENTINEL:
                name = self.new_deck_name.text().strip()
                if not name:
                    QMessageBox.warning(self, "Name required", "Give the new deck a name first.")
                    return
                deck_id = commit_candidates_to_new_deck(
                    conn, name, self.candidates, front_fields=front_fields, back_fields=back_fields,
                )
            else:
                deck_id = target
                commit_candidates_to_deck(
                    conn, deck_id, self.candidates, front_fields=front_fields, back_fields=back_fields,
                )

        QMessageBox.information(self, "Imported", "Cards imported successfully.")
        self._reset()
        self.imported.emit(deck_id)

    def _cancel(self) -> None:
        self._reset()
        self.cancelled.emit()

    def _reset(self) -> None:
        self.candidates = []
        self.pdf_path = None
        self.file_label.setText("No file selected")
        self.new_deck_name.clear()
        self.card_type_combo.setCurrentIndex(0)
        self.extra_field_keys = []
        self.table.setRowCount(0)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Include", "Front", "Back", "Confidence"])
        self.available_list.clear()
        self.front_list.clear()
        self.back_list.clear()
        self._update_count_label()
