from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QScrollArea,
    QScrollBar,
    QVBoxLayout,
    QWidget,
)

from tcalc.ui.widgets.calc.display.expression import Expression

from ....config import calc_config
from ...utils import apply_scaled_fonts
from .style import apply_display_style


class Display(QWidget):
    expression_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("displayWidget")

        _display = calc_config["display"]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            _display["margin"],
            _display["margin"],
            _display["margin"],
            _display["margin"],
        )
        layout.setSpacing(_display["spacing"])

        self.editor = Expression(self)
        self.editor.setObjectName("displayExpressionEditor")
        self.expression = self.editor

        self.editor.plain_text_changed.connect(self._on_expression_changed)
        self.editor.plain_text_changed.connect(self._update_fonts)

        self._expr_scroll = QScrollArea(self)
        self._expr_scroll.setObjectName("displayExpression")
        self._expr_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._expr_scroll.setWidgetResizable(True)
        self._expr_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._expr_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._expr_scroll.setWidget(self.editor)

        self._scroll_target: QLineEdit | None = None
        self._scroll_scheduled = False

        self._anim_duration = int(_display["scroll_anim_duration"])
        self._anim_curve = QEasingCurve.Type[_display["scroll_anim_curve"]]
        self._h_anim = self._make_scroll_anim(
            self._expr_scroll.horizontalScrollBar(), self._anim_duration, self._anim_curve
        )
        self._v_anim = self._make_scroll_anim(
            self._expr_scroll.verticalScrollBar(), self._anim_duration, self._anim_curve
        )

        self._expr_scroll.horizontalScrollBar().rangeChanged.connect(self._on_scroll_range_changed)
        self._expr_scroll.verticalScrollBar().rangeChanged.connect(self._on_scroll_range_changed)

        self.editor.input_created.connect(self._watch_cursor)
        self.editor.focused_input_changed.connect(lambda le: self._schedule_scroll(le))

        layout.addWidget(self._expr_scroll)

        line = QFrame(self)
        line.setObjectName("displayDivider")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        self.result_label = QLabel("0", self)
        self.result_label.setObjectName("displayResult")

        result_font = QFont()
        result_font.setPointSize(_display["result_font_size"])
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
        rslt_max_pt = int(calc_config["display"]["rslt_max_pt"])
        apply_scaled_fonts(
            self,
            [self.result_label],
            rslt_max_pt // 2,
            rslt_max_pt,
        )
        self.editor.update_input_fonts(self._expr_scroll)
        self._schedule_scroll(self.editor._resolve_target())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_fonts()

    #
    #
    # ==== Scrolization ====

    @staticmethod
    def _make_scroll_anim(
        bar: QScrollBar, duration: int, curve: QEasingCurve.Type
    ) -> QPropertyAnimation:
        anim = QPropertyAnimation(bar, b"value", bar)
        anim.setDuration(duration)
        anim.setEasingCurve(curve)
        return anim

    @staticmethod
    def _scroll_axis(
        bar: QScrollBar, anim: QPropertyAnimation, start: int, end: int, viewport: int, pad: int
    ) -> None:
        current = bar.value()
        if end > current + viewport - pad:
            target = end - viewport + pad
        elif start < current + pad:
            target = start - pad
        else:
            return
        target = max(0, min(target, bar.maximum()))
        if target == bar.value():
            return
        anim.stop()
        anim.setStartValue(bar.value())
        anim.setEndValue(target)
        anim.start()

    def _watch_cursor(self, le: QLineEdit) -> None:
        le.cursorPositionChanged.connect(lambda _o, _n, w=le: self._schedule_scroll(w))

    def _schedule_scroll(self, le: QLineEdit) -> None:
        self._scroll_target = le
        if self._scroll_scheduled:
            return
        self._scroll_scheduled = True
        QTimer.singleShot(0, self._flush_scroll)

    def _flush_scroll(self) -> None:
        self._scroll_scheduled = False
        le = self._scroll_target
        if le is not None and self.editor.isAncestorOf(le):
            self._scroll_to_cursor(le)

    def _on_scroll_range_changed(self, _min: int, _max: int) -> None:
        le = self._scroll_target
        if le is not None and self.editor.isAncestorOf(le):
            self._scroll_to_cursor(le)

    def _scroll_to_cursor(self, le: QLineEdit) -> None:
        viewport = self._expr_scroll.viewport()
        mapped_tl = le.mapTo(self.editor, le.cursorRect().topLeft())
        mapped_br = le.mapTo(self.editor, le.cursorRect().bottomRight())
        fm = le.fontMetrics()

        self._scroll_axis(
            self._expr_scroll.horizontalScrollBar(),
            self._h_anim,
            mapped_tl.x(),
            mapped_br.x(),
            viewport.width(),
            max(16, fm.averageCharWidth() * 2),
        )
        self._scroll_axis(
            self._expr_scroll.verticalScrollBar(),
            self._v_anim,
            mapped_tl.y(),
            mapped_br.y(),
            viewport.height(),
            max(8, fm.height() // 2),
        )

    def _on_expression_changed(self, text: str) -> None:
        self.expression_changed.emit(text)
