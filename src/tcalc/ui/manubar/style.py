from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMenuBar

from tcalc.ui.config import manubar_style
from tcalc.ui.styles import build_subs, load_qss

_QSS = Path(__file__).with_suffix(".qss")


def apply_menu_styles(menu_bar: QMenuBar) -> None:
    subs = build_subs()
    for k, v in manubar_style.items():
        subs[k] = str(int(v))

    sheet = load_qss(_QSS, subs)
    menu_bar.setStyleSheet(sheet)
