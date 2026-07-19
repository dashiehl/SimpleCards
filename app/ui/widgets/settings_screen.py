from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.theming.fonts import CANDIDATE_FONTS, installed_fonts
from app.ui import settings_store


class SettingsScreen(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(14)

        top_row = QHBoxLayout()
        back_btn = QPushButton("< Decks")
        back_btn.setObjectName("Secondary")
        back_btn.clicked.connect(self.back_requested.emit)
        top_row.addWidget(back_btn)
        title = QLabel("Settings")
        title.setObjectName("AppTitle")
        top_row.addWidget(title)
        top_row.addStretch()
        outer.addLayout(top_row)

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("App font"))
        self.font_combo = QComboBox()
        self.font_combo.currentTextChanged.connect(self._on_font_changed)
        font_row.addWidget(self.font_combo)
        font_row.addStretch()
        outer.addLayout(font_row)

        hint = QLabel(
            "Only fonts already installed on this computer are listed. Install a font like "
            "Inter, Nunito, or Poppins system-wide to add it here."
        )
        hint.setObjectName("DeckMeta")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        outer.addStretch()

        self._populate_fonts()

    def _populate_fonts(self) -> None:
        available = installed_fonts(CANDIDATE_FONTS)
        current = QApplication.font().family()
        if current and current not in available:
            available = [current] + available

        self.font_combo.blockSignals(True)
        self.font_combo.clear()
        self.font_combo.addItems(available)
        index = self.font_combo.findText(current)
        if index >= 0:
            self.font_combo.setCurrentIndex(index)
        self.font_combo.blockSignals(False)

    def _on_font_changed(self, family: str) -> None:
        if not family:
            return
        QApplication.instance().setFont(QFont(family))
        settings_store.set_font_family(family)
