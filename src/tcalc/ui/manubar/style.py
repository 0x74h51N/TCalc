from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMenuBar

from tcalc.theme import get_theme
from tcalc.ui.config import manubar_style
from tcalc.ui.styles import build_subs, load_qss

_QSS = Path(__file__).with_suffix(".qss")


def apply_menu_styles(menu_bar: QMenuBar) -> None:
    subs = build_subs()
    c = get_theme().colors

    for k, v in manubar_style.items():
        subs[k] = c[v] if isinstance(v, str) else str(int(v))

    sheet = load_qss(_QSS, subs)
    menu_bar.setStyleSheet(sheet)
