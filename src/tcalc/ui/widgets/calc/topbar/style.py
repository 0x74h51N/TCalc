from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QWidget

from .....theme import get_theme
from ....config import calc_config
from ....styles import build_subs, load_qss
from ....utils import rgba

_QSS = Path(__file__).with_suffix(".qss")


def apply_topbar_style(widget: QWidget) -> None:
    subs = build_subs()
    c = get_theme().colors
    _topbar = calc_config["topbar"]

    mem_base = c[_topbar["memory_background_base"]]
    subs["memory_bg"] = rgba(mem_base, float(_topbar["memory_background_alpha"]))
    subs["memory_bg_hover"] = rgba(mem_base, float(_topbar["memory_background_hover_alpha"]))
    subs["memory_bg_pressed"] = rgba(mem_base, float(_topbar["memory_background_pressed_alpha"]))
    subs["memory_disabled_bg"] = rgba(
        c[_topbar["memory_disabled_base"]], float(_topbar["memory_disabled_alpha"])
    )
    subs["memory_disabled_text"] = rgba(
        c[_topbar["memory_disabled_text_base"]], float(_topbar["memory_disabled_text_alpha"])
    )
    subs["memory_pad_y"] = str(int(_topbar["memory_padding_y"]))
    subs["memory_pad_x"] = str(int(_topbar["memory_padding_x"]))

    sheet = load_qss(_QSS, subs)
    widget.setStyleSheet(sheet)
