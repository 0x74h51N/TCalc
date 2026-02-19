from __future__ import annotations

from typing import TYPE_CHECKING

import calc_native
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.ops import LatexExpr
from tcalc.ui.components.math_primitives import CurlyBrace, RoundParen, SquareBracket
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
            self.numerator.default_input().setText(tokens_to_text(self.left_tokens))
        if self.right_tokens:
            self.denominator.default_input().setText(tokens_to_text(self.right_tokens))

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

        grid.addWidget(self.base, 1, 0, 1, 1, InputAlign.LEFTB.value)

        self.exponent = ExpressionSlot(
            editor,
            kind=InputKind.SCRIPT,
            key="exponent",
            align=InputAlign.RIGHTB,
        )

        grid.addWidget(self.exponent, 0, 1, 1, 2, InputAlign.RIGHTB.value)

        self._left_slot = self.base
        self._right_slot = self.exponent
        self._top_slot = self.exponent
        self._bottom_slot = self.base
        if self.left_tokens:
            self.base.default_input().setText(tokens_to_text(self.left_tokens))
        if self.right_tokens:
            self.exponent.default_input().setText(tokens_to_text(self.right_tokens))

    def anchor_y(self) -> int:
        return self.exponent.height() + self.base.height() // 2

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

    BORDER_WIDTH = 2
    BORDER_PADDING = 2
    DEGREE_RIGHT_MARGIN = 14
    DEGREE_BOTTOM_MARGIN = 4

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

        self.degree.setContentsMargins(0, 0, self.DEGREE_RIGHT_MARGIN, self.DEGREE_BOTTOM_MARGIN)

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
        self.radicand.setContentsMargins(0, self.BORDER_PADDING, 0, 0)

        self._left_slot = self.degree
        self._right_slot = self.radicand
        self._top_slot = self.degree
        self._bottom_slot = self.radicand

        if self.left_tokens:
            self.degree.default_input().setText(tokens_to_text(self.left_tokens))
        if self.right_tokens:
            self.radicand.default_input().setText(tokens_to_text(self.right_tokens))

    def anchor_y(self) -> int:
        return self.degree.height() + self.radicand.height() // 2

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


class ParenWidget(ExpressionNode):
    """Base class for parenthesis widgets."""

    SYMBOL = None
    PAREN_KIND: calc_native.ParenKind

    def __init__(
        self,
        editor: Expression,
        open_token: calc_native.ParenToken,
        inner_tokens: list[calc_native.Token],
        close_token: calc_native.ParenToken | None = None,
    ) -> None:
        super().__init__(editor, None, None)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        self._editor = editor
        self._open_token = open_token
        self._close_token = close_token
        self._paren_kind = open_token.kind

        close_symbol = close_token.symbol if close_token is not None else None
        self._left_slot: ExpressionSlot = ExpressionSlot(
            editor,
            kind=InputKind.AUX,
            key="midSlot",
            align=InputAlign.TOP,
            paren=(open_token.symbol, close_symbol),
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._left_slot, 0, Qt.AlignmentFlag.AlignHCenter)

        self._left_slot.default_input().setText(tokens_to_text(inner_tokens))

        self._open_glyph: QWidget | None = self._create_open()
        if self._open_glyph is not None:
            self._left_slot.insert_widget(0, self._open_glyph)

        self._close_glyph: QWidget | None = None
        if close_token is not None:
            self._attach_close_glyph()

        self._left_slot._on_node_removed = self._on_inner_node_removed

    def _create_open(self) -> QWidget | None:
        """Return the opening glyph widget, or *None* to draw nothing."""
        return None

    def _create_close(self) -> QWidget | None:
        """Return the closing glyph widget, or *None* to draw nothing."""
        return None

    # Public API

    def set_close(self, close_token: calc_native.ParenToken) -> None:
        """Attach a close paren that was typed later in a different segment."""
        self._close_token = close_token
        self._left_slot._paren = (self._open_token.symbol, close_token.symbol)
        if self._close_glyph is None:
            self._attach_close_glyph()

    def to_plain_text(self) -> str:
        return self._left_slot.to_plain_text()

    def focus_default(self) -> None:
        le = self._left_slot.default_input()
        if not le.text():
            le.setFocus()

    def remove(self) -> None:
        """Remove close glyph if there is."""
        if self._close_glyph is not None:
            self._detach_close_glyph()
            self._editor._pending_parens.setdefault(self._paren_kind, []).append(self)
            return

        self._dissolve()

    def _dissolve(self) -> None:
        """Remove this ParenWidget, writing its content back as plain text."""
        stack = self._editor._pending_parens.get(self._paren_kind)
        if stack and self in stack:
            stack.remove(self)
            if not stack:
                del self._editor._pending_parens[self._paren_kind]

        plain = self.to_plain_text()

        parent = self.parent()
        if isinstance(parent, ExpressionSlot):
            idx = parent._segments.index(self)
            left = parent._segments[idx - 1] if idx > 0 else None
            if isinstance(left, QLineEdit):
                cursor = len(left.text())
                left.setText(left.text() + plain)
                parent.remove(self)
                left.setFocus()
                left.setCursorPosition(cursor + len(plain))
                return

        super().remove()

    def _on_inner_node_removed(self) -> None:
        """Called when an ExpressionNode is removed from the inner slot."""
        has_inner_node = any(isinstance(s, ExpressionNode) for s in self._left_slot._segments)
        if not has_inner_node:
            self._dissolve()

    # Internal

    def _attach_close_glyph(self) -> None:
        if self._close_token is None:
            return
        self._close_glyph = self._create_close()
        if self._close_glyph is not None:
            self._left_slot.insert_widget(len(self._left_slot._segments), self._close_glyph)

    def _detach_close_glyph(self) -> None:
        if self._close_glyph is None:
            return
        self._left_slot._layout.removeWidget(self._close_glyph)
        self._left_slot._segments.remove(self._close_glyph)
        self._close_glyph.deleteLater()
        self._close_glyph = None
        self._close_token = None
        self._left_slot._paren = (self._open_token.symbol, None)


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
