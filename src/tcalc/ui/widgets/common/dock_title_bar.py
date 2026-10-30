#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QDockWidget, QHBoxLayout, QLabel, QStyle, QToolButton, QWidget


class DockTitleBar(QWidget):
    """A dock's title bar made of ordinary child widgets, so its font follows the app font.

    QDockWidget paints its own title with the app font from when the dock was created and
    never updates it, so a theme switch would leave the old theme's font there.
    """

    def __init__(self, dock: QDockWidget) -> None:
        super().__init__(dock)
        label = QLabel(dock.windowTitle())
        dock.windowTitleChanged.connect(label.setText)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 2, 2)
        layout.setSpacing(0)
        layout.addWidget(label, 1)
        # Same metrics as Qt's own dock title buttons
        style = self.style()
        icon_size = style.pixelMetric(QStyle.PixelMetric.PM_SmallIconSize)
        if style.styleHint(QStyle.StyleHint.SH_DockWidget_ButtonsHaveFrame):
            icon_size = icon_size * 5 // 8
        margin = style.pixelMetric(QStyle.PixelMetric.PM_DockWidgetTitleBarButtonMargin)
        for icon, slot in (
            (QStyle.StandardPixmap.SP_TitleBarNormalButton, self._toggle_floating),
            (QStyle.StandardPixmap.SP_TitleBarCloseButton, dock.close),
        ):
            button = QToolButton()
            button.setIcon(style.standardIcon(icon))
            button.setIconSize(QSize(icon_size, icon_size))
            button.setFixedSize(icon_size + 2 * margin, icon_size + 2 * margin)
            button.setAutoRaise(True)
            button.clicked.connect(slot)
            layout.addWidget(button)
        self._dock = dock

    def _toggle_floating(self) -> None:
        self._dock.setFloating(not self._dock.isFloating())
