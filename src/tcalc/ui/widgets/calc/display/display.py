from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...utils import apply_scaled_fonts
from ..config import display_config, font_scale_config
from .style import apply_display_style


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
            display_config["margin"],
        )
        layout.setSpacing(display_config["spacing"])

        # Apply background styling
        apply_display_style(self)

        # Exp display
        self.expression_label = QLineEdit("", self)
        self.expression_label.setObjectName("displayExpression")
        self.expression_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        small_font = QFont()
        small_font.setPointSize(display_config["expression_font_size"])

        self.expression_label.setFont(small_font)
        self.expression_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        # Keyboard signal
        self.expression_label.textChanged.connect(self._on_expression_changed)

        layout.addWidget(self.expression_label)

        line = QFrame(self)
        line.setObjectName("displayDivider")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Res display
        self.result_label = QLabel("0", self)
        self.result_label.setObjectName("displayResult")

        result_font = QFont()
        result_font.setPointSize(display_config["result_font_size"])
        result_font.setBold(True)

        self.result_label.setFont(result_font)
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.result_label)

        self._update_fonts()
        QTimer.singleShot(0, self._update_fonts)

    def update_res(self, result_text: str) -> None:
        self.result_label.setText(result_text)

    def update_expr(self, expression_text: str) -> None:
        new_text = expression_text
        if self.expression_label.text() == new_text:
            return
        else:
            self.expression_label.setText(expression_text)

    def _update_fonts(self) -> None:
        expression_scale = font_scale_config["display_expression"]
        result_scale = font_scale_config["display_result"]
        apply_scaled_fonts(
            [
                (
                    self,
                    (self.expression_label,),
                    display_config["expression_font_size"],
                    int(expression_scale["max_pt"]),
                    int(expression_scale["divisor"]),
                ),
                (
                    self,
                    (self.result_label,),
                    display_config["result_font_size"],
                    int(result_scale["max_pt"]),
                    int(result_scale["divisor"]),
                ),
            ]
        )
        fm = self.expression_label.fontMetrics()
        height_factor = float(display_config["expression_height_factor"])
        min_height = int(display_config["expression_min_height"])
        expression_height = max(min_height, int(fm.height() * height_factor))
        self.expression_label.setFixedHeight(expression_height)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_fonts()

    def _on_expression_changed(self, text: str) -> None:
        self.expression_changed.emit(text)
