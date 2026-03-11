#
#
#
# TCalc - Copyright (C) 2026 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from tcalc.theme import get_theme
from tcalc.ui.config import side_panel_config
from tcalc.ui.widgets.utils import apply_scaled_fonts


class SidePanel(QWidget):
    """Reusable vertical side-panel container."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self._parent = parent
        self._font_targets: list[tuple[Iterable[QWidget], int, int, Callable[[], None] | None]] = []

        theme = get_theme()
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(theme.colors["background_dark"]))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        margin = side_panel_config["margin"]
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(margin, margin, margin, margin)
        self._layout.setSpacing(side_panel_config["spacing"])

        QTimer.singleShot(0, self._update_fonts)

    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        """Append *widget* to the panel layout with an optional stretch factor."""
        self._layout.addWidget(widget, stretch)

    def add_divider(self) -> None:
        """Append a horizontal divider line to the panel layout."""
        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        self._layout.addWidget(divider)

    def _update_fonts(self) -> None:
        for targets, min_pt, max_pt, callback in self._font_targets:
            apply_scaled_fonts(self, targets, min_pt, max_pt)
            if callback is not None:
                callback()

    def register_font_targets(
        self,
        targets: Iterable[QWidget],
        min_pt: int,
        max_pt: int,
        callback: Callable[[], None] | None = None,
    ) -> None:
        """Register *targets* for font scaling between *min_pt* and *max_pt*."""
        self._font_targets.append((targets, min_pt, max_pt, callback))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_fonts()
