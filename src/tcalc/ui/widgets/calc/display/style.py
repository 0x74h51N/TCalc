from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

from tcalc.theme import get_theme


def apply_display_style(widget: QWidget) -> None:
    theme = get_theme()
    palette = widget.palette()
    bg = QColor(theme.colors["background_dark"])
    palette.setColor(widget.backgroundRole(), bg)
    widget.setAutoFillBackground(True)
    widget.setPalette(palette)
