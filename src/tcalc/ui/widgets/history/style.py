from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QAbstractItemView, QListWidget

from tcalc.theme import get_theme
from tcalc.ui.props import Prop, UiRole


def apply_history_style(list_widget: QListWidget) -> None:
    list_widget.setProperty(Prop.UI_ROLE, UiRole.HISTORY_LIST)

    list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    list_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
    list_widget.setAlternatingRowColors(True)

    list_widget.viewport().setProperty(
        "textInteractionFlags",
        Qt.TextInteractionFlag.TextSelectableByMouse
        | Qt.TextInteractionFlag.TextSelectableByKeyboard,
    )

    look = get_theme().look
    font = QFont(look.fonts.family_monospace, look.history.font_size)
    font.setStyleHint(QFont.StyleHint.TypeWriter)
    list_widget.setFont(font)

    list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    list_widget.setTextElideMode(Qt.TextElideMode.ElideNone)
