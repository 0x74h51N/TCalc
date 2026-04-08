from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

from tcalc.theme import get_theme
from tcalc.ui.config import calc_config
from tcalc.ui.styles import build_subs, load_qss
from tcalc.ui.utils import rgba

_QSS = Path(__file__).with_suffix(".qss")


def apply_style(widget: QWidget) -> None:
    theme = get_theme()
    c = theme.colors

    # Palette
    palette = widget.palette()
    bg = QColor(c["background_dark"])
    palette.setColor(widget.backgroundRole(), bg)
    widget.setAutoFillBackground(True)
    widget.setPalette(palette)

    subs = build_subs()
    _result = calc_config["display"]["result"]
    subs["btn_radius"] = str(int(_result["btn_radius"]))

    for k, (base, alpha) in _result["colors"].items():
        subs[k] = rgba(c[base], float(alpha))

    sheet = load_qss(_QSS, subs)
    widget.setStyleSheet(sheet)
