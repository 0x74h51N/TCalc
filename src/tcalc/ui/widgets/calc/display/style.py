from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

from tcalc.theme import get_theme

from ..config import display_config


def _build_display_stylesheet() -> str:
    theme = get_theme()
    c = theme.colors
    divider_h = int(display_config["divider_height"])
    aux_bg = c["background_dark"]
    aux_bg_focus = c["background_light"]

    return f"""
    QLineEdit[exprInput="true"] {{
        border: none;
        background-color: transparent;
        color: {c["text_secondary"]};
        selection-background-color: {c["selection_background"]};
        selection-color: {c["selection_text"]};
    }}

    QWidget[exprSlot="true"][exprSlotKind="aux"] {{
        background-color: {aux_bg};
    }}

    QWidget[exprSlot="true"][exprSlotKind="aux"] QLineEdit[exprKind="aux"]:focus {{
        background-color: {aux_bg_focus};
    }}

    QScrollArea#displayExpression,
    QScrollArea#displayExpression QWidget#qt_scrollarea_viewport,
    QWidget#displayExpressionEditor {{
        background-color: {c["background_dark"]};
    }}

    QLabel#displayResult {{
        color: {c["text_primary"]};
    }}

    QFrame#displayDivider {{
        min-height: {divider_h}px;
        max-height: {divider_h}px;
    }}

"""


def apply_display_style(widget: QWidget) -> None:
    theme = get_theme()
    palette = widget.palette()
    bg = QColor(theme.colors["background_dark"])
    palette.setColor(widget.backgroundRole(), bg)
    widget.setAutoFillBackground(True)
    widget.setPalette(palette)
    widget.setStyleSheet(_build_display_stylesheet())
