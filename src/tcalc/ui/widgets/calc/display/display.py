from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from tcalc.ui.widgets.calc.display.expression import Expression

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

        self.editor = Expression(self)
        self.editor.setObjectName("displayExpressionEditor")
        self.expression = self.editor

        # Keyboard + editor
        self.editor.plain_text_changed.connect(self._on_expression_changed)
        self.editor.plain_text_changed.connect(self._update_fonts)

        self._expr_scroll = QScrollArea(self)
        self._expr_scroll.setObjectName("displayExpression")
        self._expr_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._expr_scroll.setWidgetResizable(True)
        self._expr_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._expr_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._expr_scroll.setWidget(self.editor)

        layout.addWidget(self._expr_scroll)

        line = QFrame(self)
        line.setObjectName("displayDivider")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        self.result_label = QLabel("0", self)
        self.result_label.setObjectName("displayResult")

        result_font = QFont()
        result_font.setPointSize(display_config["result_font_size"])
        result_font.setBold(True)

        self.result_label.setFont(result_font)
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.result_label)

        apply_display_style(self)

        self._update_fonts()
        QTimer.singleShot(0, self._update_fonts)

    def update_res(self, result_text: str) -> None:
        self.result_label.setText(result_text)

    def _update_fonts(self) -> None:
        result_scale = font_scale_config["display_result"]
        apply_scaled_fonts(
            self,
            [self.result_label],
            int(result_scale["max_pt"] * 0.5),
            int(result_scale["max_pt"]),
        )
        self.editor.update_input_fonts(self._expr_scroll)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_fonts()

    def _on_expression_changed(self, text: str) -> None:
        self.expression_changed.emit(text)

    def _scroll_expression_to_end(self) -> None:
        h = self._expr_scroll.horizontalScrollBar()
        v = self._expr_scroll.verticalScrollBar()
        h.setValue(h.maximum())
        v.setValue(v.maximum())
