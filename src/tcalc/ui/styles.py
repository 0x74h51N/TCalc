from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ..theme import get_theme


def _build_stylesheet() -> str:
    theme = get_theme()
    c = theme.colors
    s = theme.spacing
    return f"""
QToolTip {{
    background-color: {c['background_dark']};
    border: 1px solid {c['border_light']};
    border-radius: {s['radius_small']}px;
    color: {c['text_secondary']};
    padding: 2px;
}}
"""


def apply_styles(app: QApplication) -> None:
    base = app.styleSheet()
    sheet = _build_stylesheet()
    if sheet:
        combined = sheet if not base else f"{base}\n{sheet}"
        app.setStyleSheet(combined)
