from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame

from .display.display import Display
from .keypad.keypad import Keypad


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
        layout.addWidget(self.display, 3)
        
        # Horizontal line
        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setLineWidth(1)
        layout.addWidget(line)
        # Keypad
        self.keypad = Keypad(parent=self)
        layout.addWidget(self.keypad, 7)
