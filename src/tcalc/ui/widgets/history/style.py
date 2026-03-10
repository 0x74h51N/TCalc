from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QAbstractItemView, QListWidget

from tcalc.ui.config import history_style as style

from ....theme import get_theme


def apply_history_style(list_widget: QListWidget) -> None:
    theme = get_theme()
    c = theme.colors

    list_widget.setStyleSheet(
        f"""
        QListWidget {{
            background: {c["background_dark"]};
            border: none;
            outline: none;
            color: {c["text_secondary"]};
        }}
        QListWidget::item {{
            border: none;
            padding: 0px;
            text-align: right;
            background: {c["background_dark_alt"]};
        }}
        QListWidget::item:alternate {{
            background: {c["background_dark"]};
        }}
        QListWidget::item:selected {{
            background: {c["selection_background"]};
            color: {c["selection_text"]};
        }}
        """
    )

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
