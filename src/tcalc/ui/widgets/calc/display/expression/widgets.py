#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from typing import TYPE_CHECKING

import calc_native
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.ops import LatexExpr
from tcalc.ui.components.math_primitives import (
    CurlyBrace,
    ParenGlyph,
    RoundParen,
    SqrtSymbol,
    SquareBracket,
)
from tcalc.ui.widgets.calc.display.expression.expression_node import (
    ExpressionNode,
    ExpressionSlot,
    InputAlign,
    InputKind,
)

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
            editor, kind=InputKind.AUX, key="numerator", align=InputAlign.TOP
        )
        layout.addWidget(self.numerator, 0, Qt.AlignmentFlag.AlignHCenter)

        self.line = QFrame(self)
        self.line.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.line.setMinimumWidth(0)
        self.line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.line)

        self.denominator = ExpressionSlot(
            editor, kind=InputKind.AUX, key="denominator", align=InputAlign.TOP
        )

        layout.addWidget(self.denominator, 0, Qt.AlignmentFlag.AlignHCenter)

        self._left_slot = self.numerator
        self._right_slot = self.denominator
        self._top_slot = self.numerator
        self._bottom_slot = self.denominator

        if self.left_tokens:
            self.numerator.default_input().setText(calc_native.tokens_to_text(self.left_tokens))
        if self.right_tokens:
            self.denominator.default_input().setText(calc_native.tokens_to_text(self.right_tokens))

    def anchor_y(self) -> int:
        return self.numerator.height() - self.line.height() // 2

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

        grid.addWidget(self.base, 1, 0, 1, 2, InputAlign.RIGHT.value)

        self.exponent = ExpressionSlot(
            editor,
            kind=InputKind.SCRIPT,
            key="exponent",
            align=InputAlign.RIGHTB,
        )

        grid.addWidget(self.exponent, 0, 1, 1, 2, InputAlign.RIGHT.value)

        self._left_slot = self.base
        self._right_slot = self.exponent
        self._top_slot = self.exponent
        self._bottom_slot = self.base
        if self.left_tokens:
            self.base.default_input().setText(calc_native.tokens_to_text(self.left_tokens))
        if self.right_tokens:
            self.exponent.default_input().setText(calc_native.tokens_to_text(self.right_tokens))

    def anchor_y(self) -> int:
        return self.exponent.height() + self.base.height() // 2

    def focus_default(self) -> None:
        base_input = self.base.default_input()
        if not base_input.text():
            base_input.setFocus()
        else:
            self.exponent.default_input().setFocus()


class RootWidget(ExpressionNode):
    """UI node for root with radicand and degree slots."""

    OP_ID = calc_native.OpId.Root
    EXPR_KIND = calc_native.ExprKind.Root
    SYMBOL = LatexExpr.Root.symbol

    BORDER_WIDTH = 2
    BORDER_PADDING = 2
    DEGREE_RIGHT_MARGIN = 16

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

        self.degree.setContentsMargins(0, 0, self.DEGREE_RIGHT_MARGIN, 0)

        grid.addWidget(self.degree, 0, 0, 2, 1, InputAlign.LEFTB.value)

        self.sqrt_symbol = SqrtSymbol(grid)

        grid.addWidget(self.sqrt_symbol, 2, 0, 2, 4, InputAlign.RIGHT.value)
        self.radicand = ExpressionSlot(
            editor,
            kind=InputKind.AUX,
            key="radicand",
            align=InputAlign.LEFTT,
        )
        grid.addWidget(self.radicand, 2, 4, 2, 2, InputAlign.RIGHTB.value)

        self.radicand.setObjectName("radicandSlot")
        self.radicand.setContentsMargins(0, self.BORDER_PADDING, 0, 0)

        self._left_slot = self.degree
        self._right_slot = self.radicand
        self._top_slot = self.degree
        self._bottom_slot = self.radicand

        if self.left_tokens:
            self.degree.default_input().setText(calc_native.tokens_to_text(self.left_tokens))
        if self.right_tokens:
            self.radicand.default_input().setText(calc_native.tokens_to_text(self.right_tokens))

        self.dHeight = self.degree.height()

    def anchor_y(self) -> int:
        return (
            self.radicand.height()
            if self.degree.height() < self.dHeight
            else self.degree.height() + self.radicand.height() // 2
        )

    def focus_default(self) -> None:
        base_input = self.radicand.default_input()
        if not base_input.text():
            base_input.setFocus()
        else:
            self.degree.default_input().setFocus()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        h = self.radicand.sizeHint().height()
        self.sqrt_symbol.setFixedHeight(h)


class ParenWidget(ExpressionNode):
    """Base class for parenthesis widgets."""

    SYMBOL = None
    PAREN_KIND: calc_native.ParenKind

    def __init__(
        self,
        editor: Expression,
        inner_tokens: list[calc_native.Token],
        open_token: calc_native.ParenToken | None = None,
        close_token: calc_native.ParenToken | None = None,
    ) -> None:
        super().__init__(editor, None, None)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        self._editor = editor
        self._open_token = open_token
        self._close_token = close_token
        if open_token is not None:
            self._paren_kind = open_token.kind
        elif close_token is not None:
            self._paren_kind = close_token.kind

        open_symbol = open_token.symbol if open_token is not None else None
        close_symbol = close_token.symbol if close_token is not None else None

        self._left_slot: ExpressionSlot = ExpressionSlot(
            editor,
            kind=InputKind.AUX,
            key="innerSlot",
            align=InputAlign.TOP,
            paren=(open_symbol, close_symbol),
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._left_slot, 0, Qt.AlignmentFlag.AlignHCenter)

        self._left_slot.default_input().setText(calc_native.tokens_to_text(inner_tokens))

        self._open_glyph: QWidget | None = None
        if open_token is not None:
            self._open_glyph = self._create_open()
            if self._open_glyph is not None:
                self._left_slot.insert_widget(0, self._open_glyph)

        self._close_glyph: QWidget | None = None
        if close_token is not None:
            self._attach_close_glyph()

    def _create_open(self) -> QWidget | None:
        """Return the opening glyph widget, or *None* to draw nothing."""
        return None

    def _create_close(self) -> QWidget | None:
        """Return the closing glyph widget, or *None* to draw nothing."""
        return None

    # Public API

    def set_open(self, open_token: calc_native.ParenToken) -> None:
        """Reattach an open paren that was typed after the glyph was removed."""

        close_sym = self._close_token.symbol if self._close_token else None
        self._left_slot._paren = (open_token.symbol, close_sym)
        if self._open_glyph is None:
            self._open_glyph = self._create_open()
            if self._open_glyph is not None:
                self._left_slot.insert_widget(0, self._open_glyph)

    def set_close(self, close_token: calc_native.ParenToken) -> None:
        """Attach a close paren that was typed later in a different segment."""
        self._close_token = close_token
        open_sym = self._open_token.symbol if self._open_token else None
        self._left_slot._paren = (open_sym, close_token.symbol)
        if self._close_glyph is None:
            self._attach_close_glyph()

    def to_plain_text(self) -> str:
        return self._left_slot.to_plain_text()

    def focus_default(self) -> None:
        le = self._left_slot.default_input()
        if not le.text():
            le.setFocus()

    def remove(self, glyph: QWidget | None = None) -> None:
        """Remove one glyph. If both gone, dissolve."""
        if glyph is self._open_glyph:
            self._detach_open_glyph()
        elif glyph is self._close_glyph:
            self._detach_close_glyph()
            parent = self.parent()
            if isinstance(parent, ExpressionSlot):
                detached = parent.detach_right_of(self)
                if detached:
                    while detached and isinstance(detached[-1], ParenGlyph):
                        parent.insert_widget(len(parent._segments), detached.pop())
                    self.adopt_segments(detached)

        if (
            self._open_glyph is None and self._close_glyph is None
        ):  # If there is no open and close glyph dissolve ParenWidget
            parent = self.parent()
            if isinstance(parent, ExpressionSlot):
                self._editor._last_focused = parent.default_input()
            self._dissolve()
        else:
            self._editor._pending_parens.setdefault(self._paren_kind, []).append(self)

    def _dissolve(self, has_node: bool = True) -> None:
        """Serialize inner content, remove this ParenWidget, write text back."""
        stack = self._editor._pending_parens.get(self._paren_kind)
        if stack and self in stack:
            stack.remove(self)
            if not stack:
                del self._editor._pending_parens[self._paren_kind]
        if has_node:
            super().dissolve()

        super().remove()

    def adopt_segments(self, segments: list[QWidget]) -> None:
        self._left_slot.adopt_segments(segments)

    # Internal

    def _attach_close_glyph(self) -> None:
        if self._close_token is None:
            return
        self._close_glyph = self._create_close()
        if self._close_glyph is not None:
            self._left_slot.insert_widget(len(self._left_slot._segments), self._close_glyph)

    def _detach_open_glyph(self) -> None:
        if self._open_glyph is None:
            return
        self._left_slot._layout.removeWidget(self._open_glyph)
        self._left_slot._segments.remove(self._open_glyph)
        self._open_glyph.deleteLater()
        self._open_glyph = None
        self._open_token = None
        self._left_slot._paren = (None, self._close_token.symbol) if self._close_token else None

    def _detach_close_glyph(self) -> None:
        if self._close_glyph is None:
            return
        self._left_slot._layout.removeWidget(self._close_glyph)
        self._left_slot._segments.remove(self._close_glyph)
        self._close_glyph.deleteLater()
        self._close_glyph = None
        self._close_token = None
        self._left_slot._paren = (self._open_token.symbol, None) if self._open_token else None


class BraceWidget(ParenWidget):
    """Curly-brace parenthesis: ``{ … }``."""

    PAREN_KIND = calc_native.ParenKind.Brace

    def _create_open(self) -> QWidget:
        return CurlyBrace(self._left_slot, True)

    def _create_close(self) -> QWidget:
        return CurlyBrace(self._left_slot, False)


class RoundParenWidget(ParenWidget):
    """Round parenthesis: ``( … )``."""

    PAREN_KIND = calc_native.ParenKind.Paren

    def _create_open(self) -> QWidget:
        return RoundParen(self._left_slot, True)

    def _create_close(self) -> QWidget:
        return RoundParen(self._left_slot, False)


class BracketWidget(ParenWidget):
    """Square bracket: ``[ … ]``."""

    PAREN_KIND = calc_native.ParenKind.Bracket

    def _create_open(self) -> QWidget:
        return SquareBracket(self._left_slot, True)

    def _create_close(self) -> QWidget:
        return SquareBracket(self._left_slot, False)
