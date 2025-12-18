from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ..theme import get_theme
from .config import style as ui_style


def _build_stylesheet() -> str:
    theme = get_theme()
    c = theme.colors
    s = theme.spacing
    tooltip_padding = int(ui_style["tooltip_padding"])
    return f"""
QToolTip {{
    background-color: {c['background_dark']};
    border: 1px solid {c['border_light']};
    border-radius: {s['radius_small']}px;
    color: {c['text_secondary']};
    padding: {tooltip_padding}px;
}}
"""


def apply_styles(app: QApplication) -> None:
    base = app.styleSheet()
    sheet = _build_stylesheet()
    if sheet:
        combined = sheet if not base else f"{base}\n{sheet}"
        app.setStyleSheet(combined)
