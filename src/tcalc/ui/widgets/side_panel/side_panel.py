#
#
#
# TCalc - Copyright (C) 2026 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from tcalc.ui.config import CONFIG
from tcalc.ui.styles import theme_events
from tcalc.ui.widgets.utils import apply_scaled_fonts

_FontTargets = Iterable[QWidget] | Callable[[], Iterable[QWidget]]


class SidePanel(QWidget):
    """Reusable vertical side-panel container."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self._parent = parent
        self._font_targets: list[tuple[_FontTargets, int, int, Callable[[], None] | None]] = []

        self.setBackgroundRole(QPalette.ColorRole.Base)
        self.setAutoFillBackground(True)

        margin = CONFIG.side_panel.margin
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(margin, margin, margin, margin)
        self._layout.setSpacing(CONFIG.side_panel.spacing)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(CONFIG.side_panel.resize_debounce_ms)
        self._resize_timer.timeout.connect(self._update_fonts)

        QTimer.singleShot(0, self._update_fonts)
        theme_events.applied.connect(self._update_fonts)

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
            widgets = targets() if callable(targets) else targets
            apply_scaled_fonts(self, widgets, min_pt, max_pt)
            if callback is not None:
                callback()

    def register_font_targets(
        self,
        targets: _FontTargets,
        min_pt: int,
        max_pt: int,
        callback: Callable[[], None] | None = None,
    ) -> None:
        """Register *targets* for font scaling between *min_pt* and *max_pt*."""
        self._font_targets.append((targets, min_pt, max_pt, callback))

    def update_fonts(self) -> None:
        self._update_fonts()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._resize_timer.start()
