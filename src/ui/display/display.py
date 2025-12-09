from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
)
from PySide6.QtGui import QFont
from PySide6.QtGui import QColor

class Display(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("displayWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)


        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#1E1E1E"))
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        
        self.expression_label = QLabel("", self)
        self.expression_label.setObjectName("displayExpression")
        small_font = QFont()
        small_font.setPointSize(11)
        self.expression_label.setFont(small_font)
        self.expression_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.expression_label)

        line = QFrame(self)
        line.setObjectName("displayDivider")
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        self.result_label = QLabel("0", self)
        self.result_label.setObjectName("displayResult")
        result_font = QFont()
        result_font.setPointSize(20)
        result_font.setBold(True)
        self.result_label.setFont(result_font)
        self.result_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.result_label)

    def update(self, expression_text: str, result_text: str) -> None:
        self.expression_label.setText(expression_text.strip())
        self.result_label.setText(result_text)
