from __future__ import annotations

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor

from .....theme import get_theme
from ..config import display_config


def _build_display_stylesheet() -> str:
    theme = get_theme()
    c = theme.colors
    divider_h = int(display_config["divider_height"])

    return f"""
QLineEdit#displayExpression {{
    border: none;
    background-color: transparent;
    color: {c['text_secondary']};
    selection-background-color: {c['selection_background']};
    selection-color: {c['selection_text']};
}}
QLineEdit#displayExpression:focus {{
    border: none;
    background-color: transparent;
}}
QLabel#displayResult {{
    color: {c['text_primary']};
}}
QFrame#displayDivider {{
    min-height: {divider_h}px;
    max-height: {divider_h}px;
}}
"""


def apply_display_style(widget: QWidget) -> None:
    theme = get_theme()
    palette = widget.palette()
    palette.setColor(widget.backgroundRole(), QColor(theme.colors["background_dark"]))
    widget.setAutoFillBackground(True)
    widget.setPalette(palette)
    widget.setStyleSheet(_build_display_stylesheet())
