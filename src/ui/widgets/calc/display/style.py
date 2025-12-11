from __future__ import annotations

from PySide6.QtWidgets import QWidget, QLineEdit, QLabel, QFrame
from PySide6.QtGui import QColor

from .....theme import get_theme


def apply_display_style(widget: QWidget) -> None:
    theme = get_theme()
    palette = widget.palette()
    palette.setColor(widget.backgroundRole(), QColor(theme.colors["background_dark"]))
    widget.setAutoFillBackground(True)
    widget.setPalette(palette)


def apply_expression_style(line_edit: QLineEdit) -> None:
    line_edit.setObjectName("displayExpression")


def apply_result_style(label: QLabel) -> None:
    label.setObjectName("displayResult")


def apply_divider_style(frame: QFrame) -> None:
    frame.setObjectName("displayDivider")
