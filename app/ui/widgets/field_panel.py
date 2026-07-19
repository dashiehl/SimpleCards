from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.db.field_layout import label_for


class CardFacePanel(QWidget):
    """Renders an ordered list of (field_key, value) pairs for one side of a card.
    The first field is shown large as the 'headline'; the rest render as caption + value."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.addStretch()
        self._layout.addStretch()

    def set_fields(self, fields: list[tuple[str, str]]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._layout.addStretch()
        self._layout.addStretch()
        visible = [(k, v) for k, v in fields if v]

        for i, (key, value) in enumerate(visible):
            if i == 0:
                label = QLabel(value)
                label.setObjectName("CardFront")
                label.setWordWrap(True)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._layout.insertWidget(self._layout.count() - 1, label)
                continue

            if key == "forms":
                body = QLabel(value)
                body.setObjectName("CardForms")
                body.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._layout.insertWidget(self._layout.count() - 1, body)
                continue

            if key == "example":
                body = QLabel(f'"{value}"')
                body.setObjectName("CardExample")
                body.setWordWrap(True)
                body.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._layout.insertWidget(self._layout.count() - 1, body)
                continue

            caption = QLabel(label_for(key).upper())
            caption.setObjectName("FieldCaption")
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            body = QLabel(value)
            body.setObjectName("CardBack")
            body.setWordWrap(True)
            body.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._layout.insertWidget(self._layout.count() - 1, caption)
            self._layout.insertWidget(self._layout.count() - 1, body)

        if not visible:
            placeholder = QLabel("(empty)")
            placeholder.setObjectName("DeckMeta")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._layout.insertWidget(self._layout.count() - 1, placeholder)
