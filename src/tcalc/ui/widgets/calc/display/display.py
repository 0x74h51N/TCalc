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
        self.editor.plain_text_changed.connect(
            lambda _text: QTimer.singleShot(0, self._scroll_expression_to_end)
        )

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
        expr_inputs = self.editor.expression_inputs()
        main_inputs = [le for le in expr_inputs if le.property("exprKind") == "main"]
        aux_inputs = [le for le in expr_inputs if le.property("exprKind") != "main"]

        expression_scale = font_scale_config["display_expression"]
        result_scale = font_scale_config["display_result"]

        base_main = int(display_config["expression_font_size"])
        base_aux = max(8, int(base_main * 0.85))

        def append_scaled(widgets: list, base: int, scale: dict) -> None:
            if not widgets:
                return
            items.append(
                (
                    self,
                    tuple(widgets),
                    base,
                    int(scale["max_pt"]),
                    int(scale["divisor"]),
                )
            )

        items: list[tuple] = []
        append_scaled(main_inputs, base_main, expression_scale)
        append_scaled(aux_inputs, base_aux, expression_scale)
        append_scaled(
            [self.result_label],
            display_config["result_font_size"],
            result_scale,
        )

        apply_scaled_fonts(items)

        def apply_height(group: list) -> None:
            if not group:
                return
            min_height = int(display_config["expression_min_height"])
            h = min_height
            for le in group:
                le.setFixedHeight(h)

        apply_height(main_inputs)
        apply_height(aux_inputs)

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
