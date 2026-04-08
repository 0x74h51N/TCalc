#
#
#   TCalc is a native-powered scientific desktop calculator designed
#   for high-performance, precision, and a superior user experience.
#   Copyright (C) <2025>  <Tahsin Önemli>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QVBoxLayout, QWidget

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
