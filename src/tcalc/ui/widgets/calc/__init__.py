#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from ...config import calc_config
from .display.display import Display
from .topbar import TopBar


class CalcWidget(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("calcWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Display
        self.display = Display(parent=self)
        layout.addWidget(self.display, calc_config["layout"]["display_stretch"])

        # Top bar (angle + memory)
        self.topbar = TopBar(parent=self)
        self.topbar.setAutoFillBackground(True)
        self.topbar.setPalette(self.display.palette())
        layout.addWidget(self.topbar)

        # Horizontal line
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setLineWidth(calc_config["layout"]["divider_line_width"])
        layout.addWidget(line)
