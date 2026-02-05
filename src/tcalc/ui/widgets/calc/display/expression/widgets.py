from __future__ import annotations

from typing import TYPE_CHECKING

import calc_native
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLineEdit, QSizePolicy, QVBoxLayout

from tcalc.core.ops import Operation
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
    SYMBOL = Operation.FRAC.symbol

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

        if self.left_tokens:
            self.numerator.default_input().setText(tokens_to_text(self.left_tokens))
        if self.right_tokens:
            self.denominator.default_input().setText(tokens_to_text(self.right_tokens))

    def line_edits(self) -> list[QLineEdit]:
        return [*self.numerator.line_edits(), *self.denominator.line_edits()]

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
    SYMBOL = Operation.POWw.symbol

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
            kind=InputKind.AUX,
            key="exponent",
            align=InputAlign.LEFTB,
        )

        self.exponent.setProperty("exprSlotExponent", True)

        grid.addWidget(self.exponent, 0, 0, 1, 2, InputAlign.RIGHTB.value)

        grid.setRowStretch(0, 0)
        grid.setRowStretch(1, 1)

        self._left_slot = self.base
        self._right_slot = self.exponent

        if self.left_tokens:
            self.base.default_input().setText(tokens_to_text(self.left_tokens))
        if self.right_tokens:
            self.exponent.default_input().setText(tokens_to_text(self.right_tokens))

    def line_edits(self) -> list[QLineEdit]:
        return [*self.base.line_edits(), *self.exponent.line_edits()]

    def focus_default(self) -> None:
        base_input = self.base.default_input()
        if not base_input.text():
            base_input.setFocus()
        else:
            self.exponent.default_input().setFocus()
