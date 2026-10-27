from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QWidget

from tcalc.ui.config import calc_config, keypad_config
from tcalc.ui.styles import build_subs, load_qss

_QSS = Path(__file__).with_suffix(".qss")


def apply_keypad_style(widget: QWidget) -> None:
    subs = build_subs()
    _style = calc_config["style"]

    subs["button_padding"] = str(int(keypad_config["button_padding"]))
    for k, v in _style.items():
        if isinstance(v, int):
            subs[k] = str(v)

    sheet = load_qss(_QSS, subs)
    widget.setStyleSheet(sheet)
