from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
    QLineEdit
)
from PySide6.QtGui import QFont

from ..config import display_config
from .style import apply_display_style, apply_expression_style, apply_result_style, apply_divider_style


class Display(QWidget):
    expression_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("displayWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            display_config["margin"],
            display_config["margin"],
            display_config["margin"],
            display_config["margin"]
        )
        layout.setSpacing(display_config["spacing"])

        # Apply background styling
        apply_display_style(self)
        
        #Exp display
        self.expression_label = QLineEdit("", self)
        apply_expression_style(self.expression_label)
        
        small_font = QFont()
        small_font.setPointSize(display_config["expression_font_size"])

        self.expression_label.setFont(small_font)
        self.expression_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        #Keyboard signal
        self.expression_label.textChanged.connect(self._on_expression_changed)

        layout.addWidget(self.expression_label)

        line = QFrame(self)
        apply_divider_style(line)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        #Res display
        self.result_label = QLabel("0", self)
        apply_result_style(self.result_label)

        result_font = QFont()
        result_font.setPointSize(display_config["result_font_size"])
        result_font.setBold(True)

        self.result_label.setFont(result_font)
        self.result_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.result_label)

    def update_res(self, result_text: str) -> None:
        self.result_label.setText(result_text)

    def update_expr(self, expression_text: str) -> None:
        self.expression_label.setText(expression_text.strip())

    def _on_expression_changed(self, text: str) -> None:
        self.expression_changed.emit(text)