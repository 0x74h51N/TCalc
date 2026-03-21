from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QAbstractItemView, QListWidget

from tcalc.ui.config import calc_config
from tcalc.ui.config import history_style as style

from ....theme import get_theme
from ...styles import build_subs, load_qss

_QSS = Path(__file__).with_suffix(".qss")


def apply_history_style(list_widget: QListWidget) -> None:
    theme = get_theme()

    list_widget.setProperty("uiRole", "historyList")

    list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    list_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
    list_widget.setAlternatingRowColors(True)

    list_widget.viewport().setProperty(
        "textInteractionFlags",
        Qt.TextInteractionFlag.TextSelectableByMouse
        | Qt.TextInteractionFlag.TextSelectableByKeyboard,
    )

    font = QFont(theme.fonts["family_monospace"], style["font_size"])
    font.setStyleHint(QFont.StyleHint.TypeWriter)
    list_widget.setFont(font)

    list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    list_widget.setTextElideMode(Qt.TextElideMode.ElideNone)

    subs = build_subs()
    subs["root_border_width"] = str(int(calc_config["display"]["root_border_width"]))

    sheet = load_qss(_QSS, subs)
    list_widget.setStyleSheet(sheet)
