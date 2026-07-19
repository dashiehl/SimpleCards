from __future__ import annotations

from PySide6.QtCore import QSettings

from app.config import APP_NAME


def _settings() -> QSettings:
    return QSettings(APP_NAME, APP_NAME)


def get_font_family() -> str | None:
    value = _settings().value("font_family", None)
    return str(value) if value else None


def set_font_family(family: str) -> None:
    _settings().setValue("font_family", family)
