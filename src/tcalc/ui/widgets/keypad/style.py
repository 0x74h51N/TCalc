from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QWidget

from ....theme import get_theme
from ...config import calc_config, keypad_config
from ...styles import build_subs, load_qss
from ...utils import rgba

_QSS = Path(__file__).with_suffix(".qss")


def apply_keypad_style(widget: QWidget) -> None:
    subs = build_subs()
    c = get_theme().colors

    _style = calc_config["style"]

    subs["disabled_bg"] = rgba(
        c[_style["disabled_background_base"]], float(_style["disabled_background_alpha"])
    )
    subs["disabled_text"] = rgba(
        c[_style["disabled_text_base"]], float(_style["disabled_text_alpha"])
    )
    subs["button_padding"] = str(int(keypad_config["button_padding"]))
    subs["compact_pad_y"] = str(int(_style["compact_button_padding_y"]))
    subs["compact_pad_x"] = str(int(_style["compact_button_padding_x"]))

    sheet = load_qss(_QSS, subs)
    widget.setStyleSheet(sheet)
