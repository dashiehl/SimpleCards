from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QTextEdit, QVBoxLayout,
)

from app.db.models import Card

KIND_LABELS = {
    "basic": "Basic (front / back)",
    "multi_field": "Multi-field (front / back / forms / example)",
    "cloze": "Cloze deletion (fill-in-the-blank)",
}


class CardEditorDialog(QDialog):
    """Add or edit a single card. `card` is None for a new card."""

    def __init__(self, card: Card | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Card" if card else "Add Card")
        self.setMinimumWidth(480)
        self._card = card

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.kind_combo = QComboBox()
        for key, label in KIND_LABELS.items():
            self.kind_combo.addItem(label, key)
        self.kind_combo.currentIndexChanged.connect(self._on_kind_changed)
        form.addRow("Card type", self.kind_combo)

        self.front_edit = QLineEdit()
        form.addRow("Front", self.front_edit)

        self.back_edit = QTextEdit()
        self.back_edit.setFixedHeight(70)
        form.addRow("Back", self.back_edit)

        self.forms_edit = QLineEdit()
        self.forms_row_label = QLabel("Forms")
        form.addRow(self.forms_row_label, self.forms_edit)

        self.example_edit = QLineEdit()
        self.example_row_label = QLabel("Example")
        form.addRow(self.example_row_label, self.example_edit)

        self.cloze_edit = QTextEdit()
        self.cloze_edit.setFixedHeight(90)
        self.cloze_edit.setPlaceholderText('Use {{c1::answer}} to mark a blank, e.g. "The mitochondria is the {{c1::powerhouse}} of the cell."')
        self.cloze_row_label = QLabel("Cloze text")
        form.addRow(self.cloze_row_label, self.cloze_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("comma, separated, tags")
        form.addRow("Tags", self.tags_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if card:
            self._load(card)
        else:
            self._on_kind_changed()

    def _load(self, card: Card) -> None:
        index = self.kind_combo.findData(card.kind)
        self.kind_combo.setCurrentIndex(max(index, 0))
        self.front_edit.setText(card.front)
        self.back_edit.setPlainText(card.back or "")
        self.forms_edit.setText(card.extra_fields.get("forms", ""))
        self.example_edit.setText(card.extra_fields.get("example", ""))
        self.cloze_edit.setPlainText(card.extra_fields.get("cloze_text", ""))
        self.tags_edit.setText(", ".join(card.tags))
        self._on_kind_changed()

    def _on_kind_changed(self) -> None:
        kind = self.kind_combo.currentData()
        is_cloze = kind == "cloze"
        is_multi = kind == "multi_field"

        self.front_edit.setVisible(not is_cloze)
        self.back_edit.setVisible(not is_cloze)
        self.cloze_edit.setVisible(is_cloze)
        self.cloze_row_label.setVisible(is_cloze)

        self.forms_edit.setVisible(is_multi)
        self.forms_row_label.setVisible(is_multi)
        self.example_edit.setVisible(is_multi)
        self.example_row_label.setVisible(is_multi)

    def result_card(self, deck_id: int) -> Card:
        kind = self.kind_combo.currentData()
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        extra_fields = {}

        if kind == "cloze":
            cloze_text = self.cloze_edit.toPlainText().strip()
            extra_fields["cloze_text"] = cloze_text
            front, back = cloze_text, cloze_text
        else:
            front = self.front_edit.text().strip()
            back = self.back_edit.toPlainText().strip()
            if kind == "multi_field":
                if self.forms_edit.text().strip():
                    extra_fields["forms"] = self.forms_edit.text().strip()
                if self.example_edit.text().strip():
                    extra_fields["example"] = self.example_edit.text().strip()

        base = self._card or Card(id=None, deck_id=deck_id)
        base.kind = kind
        base.front = front
        base.back = back
        base.extra_fields = extra_fields
        base.tags = tags
        base.deck_id = deck_id
        return base
