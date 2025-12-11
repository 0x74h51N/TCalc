from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ..theme import get_theme


def _build_stylesheet() -> str:
    return ""


def apply_styles(app: QApplication) -> None:
    base = app.styleSheet()
    sheet = _build_stylesheet()
    if sheet:
        combined = sheet if not base else f"{base}\n{sheet}"
        app.setStyleSheet(combined)
