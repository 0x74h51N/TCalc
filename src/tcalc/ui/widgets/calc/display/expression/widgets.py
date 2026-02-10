from __future__ import annotations

from typing import TYPE_CHECKING

import calc_native
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.ops import LatexExpr
from tcalc.ui.widgets.calc.display.expression.expression_node import (
    ExpressionNode,
    ExpressionSlot,
    InputAlign,
    InputKind,
)

from .utils import tokens_to_text

if TYPE_CHECKING:
    from .expression import Expression


class FractionWidget(ExpressionNode):
    """UI node for a fraction with numerator and denominator slots."""

    OP_ID = calc_native.OpId.Div
    EXPR_KIND = calc_native.ExprKind.Frac
    SYMBOL = LatexExpr.Frac.symbol

    def __init__(
        self,
        editor: Expression,
        left_tokens: list[calc_native.Token] | None = None,
        right_tokens: list[calc_native.Token] | None = None,
    ) -> None:
        super().__init__(editor, left_tokens, right_tokens)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.numerator = ExpressionSlot(
            editor, kind=InputKind.AUX, key="numerator", align=InputAlign.CENTER
        )
        layout.addWidget(self.numerator, 0, Qt.AlignmentFlag.AlignHCenter)

        self.line = QFrame(self)
        self.line.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.line.setMinimumWidth(0)
        self.line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.line)

        self.denominator = ExpressionSlot(
            editor, kind=InputKind.AUX, key="denominator", align=InputAlign.CENTER
        )
        layout.addWidget(self.denominator, 0, Qt.AlignmentFlag.AlignHCenter)

        self._left_slot = self.numerator
        self._right_slot = self.denominator
        self._top_slot = self.numerator
        self._bottom_slot = self.denominator

        if self.left_tokens:
            self.numerator.default_input().setText(tokens_to_text(self.left_tokens))
        if self.right_tokens:
            self.denominator.default_input().setText(tokens_to_text(self.right_tokens))

    def focus_default(self) -> None:
        num_input = self.numerator.default_input()
        if not num_input.text():
            num_input.setFocus()
        else:
            self.denominator.default_input().setFocus()


class PowWidget(ExpressionNode):
    """UI node for power/exponent with base and exponent slots."""

    OP_ID = calc_native.OpId.Pow
    EXPR_KIND = calc_native.ExprKind.Pow
    SYMBOL = LatexExpr.Pow.symbol

    def __init__(
        self,
        editor: Expression,
        left_tokens: list[calc_native.Token] | None = None,
        right_tokens: list[calc_native.Token] | None = None,
    ) -> None:
        super().__init__(editor, left_tokens, right_tokens)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        grid.setVerticalSpacing(0)
        grid.setHorizontalSpacing(0)

        self.base = ExpressionSlot(
            editor,
            kind=InputKind.AUX,
            key="base",
            align=InputAlign.LEFT,
        )

        grid.addWidget(self.base, 1, 0, 1, 1, InputAlign.LEFTB.value)

        self.exponent = ExpressionSlot(
            editor,
            kind=InputKind.SCRIPT,
            key="exponent",
            align=InputAlign.RIGHTB,
        )

        grid.addWidget(self.exponent, 0, 0, 1, 2, InputAlign.RIGHTB.value)

        self._left_slot = self.base
        self._right_slot = self.exponent
        self._top_slot = self.exponent
        self._bottom_slot = self.base
        if self.left_tokens:
            self.base.default_input().setText(tokens_to_text(self.left_tokens))
        if self.right_tokens:
            self.exponent.default_input().setText(tokens_to_text(self.right_tokens))

    def focus_default(self) -> None:
        base_input = self.base.default_input()
        if not base_input.text():
            base_input.setFocus()
        else:
            self.exponent.default_input().setFocus()


class SqrtSymbol(QWidget):
    """Custom widget that draws a scalable √ symbol."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = Qt.GlobalColor.white
        self.setMinimumWidth(25)

    def setColor(self, color):
        self._color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(self._color)
        pen.setWidth(2)
        painter.setPen(pen)

        w, h = self.width(), self.height()

        path = QPainterPath()
        path.moveTo(0, h * 0.35)
        path.lineTo(w * 0.25, h * 0.35)
        path.lineTo(w * 0.45, h)
        path.lineTo(w, 0)

        painter.drawPath(path)


class RootWidget(ExpressionNode):
    """UI node for root with radicand and degree slots."""

    OP_ID = calc_native.OpId.Root
    EXPR_KIND = calc_native.ExprKind.Root
    SYMBOL = LatexExpr.Root.symbol

    def __init__(
        self,
        editor: Expression,
        left_tokens: list[calc_native.Token] | None = None,
        right_tokens: list[calc_native.Token] | None = None,
    ) -> None:
        super().__init__(editor, left_tokens, right_tokens)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setAlignment(Qt.AlignmentFlag.AlignBottom)
        grid.setSpacing(0)
        grid.setVerticalSpacing(0)
        grid.setHorizontalSpacing(0)

        self.degree = ExpressionSlot(
            editor,
            kind=InputKind.SCRIPT,
            key="degree",
            align=InputAlign.LEFTT,
        )

        self.degree.setContentsMargins(0, 0, 14, 4)

        grid.addWidget(self.degree, 0, 0, 3, 1, InputAlign.LEFTB.value)

        self.sqrt_symbol = SqrtSymbol()

        grid.addWidget(self.sqrt_symbol, 1, 0, 6, 4, InputAlign.RIGHTT.value)
        self.radicand = ExpressionSlot(
            editor,
            kind=InputKind.AUX,
            key="radicand",
            align=InputAlign.LEFT,
        )
        grid.addWidget(self.radicand, 1, 4, 6, 2, InputAlign.RIGHTB.value)

        self.radicand.setObjectName("radicandSlot")
        self.radicand.setContentsMargins(0, 2, 0, 0)

        self._left_slot = self.degree
        self._right_slot = self.radicand
        self._top_slot = self.degree
        self._bottom_slot = self.radicand

        if self.left_tokens:
            self.degree.default_input().setText(tokens_to_text(self.left_tokens))
        if self.right_tokens:
            self.radicand.default_input().setText(tokens_to_text(self.right_tokens))

    def focus_default(self) -> None:
        base_input = self.radicand.default_input()
        if not base_input.text():
            base_input.setFocus()
        else:
            self.degree.default_input().setFocus()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        h = self.radicand.height()
        self.sqrt_symbol.setFixedHeight(h)
