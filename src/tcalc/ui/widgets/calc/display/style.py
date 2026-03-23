from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

from tcalc.theme import get_theme
from tcalc.ui.config import calc_config
from tcalc.ui.styles import build_subs, load_qss

_QSS = Path(__file__).with_suffix(".qss")


def apply_display_style(widget: QWidget) -> None:
    theme = get_theme()

    # Palette
    palette = widget.palette()
    bg = QColor(theme.colors["background_dark"])
    palette.setColor(widget.backgroundRole(), bg)
    widget.setAutoFillBackground(True)
    widget.setPalette(palette)

    # QSS
    subs = build_subs()
    _display = calc_config["display"]
    subs["divider_height"] = str(int(_display["divider_height"]))
    subs["root_border_width"] = str(int(_display["root_border_width"]))

    sheet = load_qss(_QSS, subs)
    widget.setStyleSheet(sheet)
