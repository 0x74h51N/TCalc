from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QWidget

from tcalc.theme import get_theme
from tcalc.ui.config import calc_config
from tcalc.ui.styles import build_subs, load_qss
from tcalc.ui.utils import rgba

_QSS = Path(__file__).with_suffix(".qss")


def apply_topbar_style(widget: QWidget) -> None:
    subs = build_subs()
    c = get_theme().colors
    _topbar = calc_config["topbar"]

    for k, v in _topbar.items():
        if isinstance(v, int):
            subs[k] = str(v)

    for k, (base, alpha) in _topbar["memory_colors"].items():
        subs[k] = rgba(c[base], float(alpha))

    sheet = load_qss(_QSS, subs)
    widget.setStyleSheet(sheet)
