from __future__ import annotations

from PySide6.QtCore import Property, Qt
from PySide6.QtWidgets import QFrame, QLabel, QStackedLayout

from app.theming.animations import make_flip_animation


class CardFlipWidget(QFrame):
    """A card surface that can flip between arbitrary front/back content widgets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumHeight(320)

        self._scale = 1.0
        self._base_pixmap = None

        self.content_layout = QStackedLayout(self)
        self.content_layout.setContentsMargins(32, 32, 32, 32)

        self.overlay = QLabel(self)
        self.overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overlay.hide()
        self.overlay.raise_()

    def get_flip_scale(self) -> float:
        return self._scale

    def set_flip_scale(self, value: float) -> None:
        self._scale = value
        if value >= 0.999 or self._base_pixmap is None:
            self.overlay.hide()
            return
        pix = self._base_pixmap
        w = max(1, int(pix.width() * value))
        scaled = pix.scaled(w, pix.height(), Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        self.overlay.setPixmap(scaled)
        self.overlay.setGeometry(self.rect())
        self.overlay.show()
        self.overlay.raise_()

    flip_scale = Property(float, get_flip_scale, set_flip_scale)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())

    def flip_to(self, swap_content_fn) -> None:
        """Animate a flip; `swap_content_fn` is called at the midpoint to change what's shown."""
        self._base_pixmap = self.grab()

        def on_midpoint():
            swap_content_fn()
            self._base_pixmap = self.grab()

        self._animation = make_flip_animation(self, on_midpoint)
        self._animation.start()
