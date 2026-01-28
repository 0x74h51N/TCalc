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

from .utils import (
    parenter,
    tokens_to_text,
)

if TYPE_CHECKING:
    from .expression import Expression


class FractionWidget(ExpressionNode):
    """UI node for a fraction with numerator and denominator slots."""

    OP_ID = calc_native.OpId.Div

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

    def to_plain_text(self) -> str:
        # TODO: tokens-first or cached structure
        # this setup does pointless text->token->text juggling and causes unnecessary conversions

        num_text = self.numerator.to_plain_text()
        den_text = self.denominator.to_plain_text()

        num_serial = parenter(calc_native.tokenize_string(num_text))
        den_serial = parenter(calc_native.tokenize_string(den_text))

        fraction_text = f"{num_serial}{Operation.DIV.symbol}{den_serial}"
        return parenter(fraction_text)


class PowWidget(ExpressionNode):
    """UI node for power/exponent with base and exponent slots."""

    OP_ID = calc_native.OpId.Pow

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

    def to_plain_text(self) -> str:
        base_text = self.base.to_plain_text()
        exp_text = self.exponent.to_plain_text()

        base_serial = parenter(calc_native.tokenize_string(base_text))
        exp_serial = parenter(calc_native.tokenize_string(exp_text))

        pow_text = f"{base_serial}{Operation.POW.symbol}{exp_serial}"
        return parenter(pow_text)
