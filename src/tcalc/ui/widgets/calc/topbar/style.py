from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QWidget

from tcalc.ui.config import calc_config
from tcalc.ui.styles import build_subs, load_qss

_QSS = Path(__file__).with_suffix(".qss")


def apply_topbar_style(widget: QWidget) -> None:
    subs = build_subs()
    _topbar = calc_config["topbar"]

    for k, v in _topbar.items():
        if isinstance(v, int):
            subs[k] = str(v)

    sheet = load_qss(_QSS, subs)
    widget.setStyleSheet(sheet)
