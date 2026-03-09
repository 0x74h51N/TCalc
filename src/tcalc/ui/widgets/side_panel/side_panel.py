#
#
#
# TCalc - Copyright (C) 2026 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from tcalc.theme import get_theme
from tcalc.ui.config import side_panel_config


class SidePanel(QWidget):
    """Reusable vertical side-panel container."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidePanel")

        self._font_targets: list[tuple[QWidget, int, int]] = []

        theme = get_theme()
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(theme.colors["background_dark"]))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        margin = side_panel_config["margin"]
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(margin, margin, margin, margin)
        self._layout.setSpacing(side_panel_config["spacing"])

    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        """Append *widget* to the panel layout with an optional stretch factor."""
        self._layout.addWidget(widget, stretch)

    def add_divider(self) -> None:
        """Append a horizontal divider line to the panel layout."""
        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        self._layout.addWidget(divider)
