from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from tcalc.ui.config import memory_style as style


class MemoryBar(QWidget):
    """Memorized value bar"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("memoryBarWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(int(style["divider_spacing"]))

        row = QWidget(self)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        self._memory_label = QLabel("Mem:", row)
        self._memory_value = QLabel("", row)
        self._memory_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        row_layout.addWidget(self._memory_label, 0)
        row_layout.addWidget(self._memory_value, 1)

        self._memory_divider = QFrame(self)
        self._memory_divider.setFrameShape(QFrame.Shape.HLine)
        self._memory_divider.setFrameShadow(QFrame.Shadow.Sunken)

        layout.addWidget(row)
        layout.addWidget(self._memory_divider)

        self.setVisible(False)
        self._memory_divider.setVisible(False)

    def set_memory(self, text: str) -> None:
        """Set and show memorised values on Memory bar"""
        if text:
            self._memory_value.setText(text)
            self.setVisible(True)
            self._memory_divider.setVisible(True)
        else:
            self.setVisible(False)
            self._memory_divider.setVisible(False)
