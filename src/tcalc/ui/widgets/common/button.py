#
#
#
# TCalc - Copyright (C) 2026 Tahsin Onemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QWidget

from tcalc.theme import get_theme


class IconButton(QPushButton):
    """Themed push button with an icon and optional label text."""

    def __init__(
        self,
        icon_name: str,
        tooltip: str = "",
        text: str = "",
        size: int | None = None,
        parent: QWidget | None = None,
        padding: int = 4,
    ) -> None:
        super().__init__(text, parent)
        self.setIcon(QIcon.fromTheme(icon_name))

        if tooltip:
            self.setToolTip(tooltip)

        theme = get_theme()
        c = theme.colors
        radius = theme.spacing["radius_small"]

        self.setStyleSheet(
            f"QPushButton {{ background: {c['background_light']};"
            f" border: none; border-radius: {radius}px;"
            f" padding: {padding}px; }}"
            f" QPushButton:hover {{ background: {c['selection_background']}; }}"
        )

        if size is not None:
            self.setFixedSize(size, size)
            self.setFlat(True)
