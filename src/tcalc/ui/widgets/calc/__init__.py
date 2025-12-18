from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from .config import layout_config
from .display.display import Display
from .keypad.keypad import Keypad
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
        layout.addWidget(self.display, layout_config["display_stretch"])

        # Top bar (angle + memory)
        self.topbar = TopBar(parent=self)
        self.topbar.setAutoFillBackground(True)
        self.topbar.setPalette(self.display.palette())
        layout.addWidget(self.topbar)

        # Keypad
        self.keypad = Keypad(parent=self)

        # Horizontal line
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setLineWidth(layout_config["divider_line_width"])
        layout.addWidget(line)
        # Keypad
        layout.addWidget(self.keypad, layout_config["keypad_stretch"])
