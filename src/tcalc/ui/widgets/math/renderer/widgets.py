#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from typing import ClassVar

import calc_native
from PySide6.QtCore import QEvent, QSize, Qt
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
from tcalc.ui.widgets.utils import InputAlign

from ..math_primitives import (
    SCRIPT_DROP,
    SCRIPT_GAP_X,
    CurlyBrace,
    ParenGlyph,
    RoundParen,
    SqrtSymbol,
    SquareBracket,
)
from .expression_node import (
    ExpressionNode,
    ExpressionSlot,
    InputKind,
)

# Single source for paren glyph chars per ParenKind. The native paren_table
# was removed with the unified ParenToken model, so the UI keeps a tiny
# Python-side mapping here.
_PAREN_GLYPHS: dict[calc_native.ParenKind, tuple[str, str]] = {
    calc_native.ParenKind.Paren: ("(", ")"),
    calc_native.ParenKind.Bracket: ("[", "]"),
    calc_native.ParenKind.Brace: ("{", "}"),
}


def paren_glyph(kind: calc_native.ParenKind) -> tuple[str, str]:
    return _PAREN_GLYPHS[kind]


def _empty_tail_w(slot: ExpressionSlot) -> int:
    """Width of *slot*'s trailing cursor slot while it holds no text."""
    tail = slot._segments[-1]
    return tail.width() if isinstance(tail, QLineEdit) and not tail.text() else 0


class FractionWidget(ExpressionNode):
    """UI node for a fraction with numerator and denominator slots."""

    OP_ID = calc_native.OpId.Div
    LATEX_KIND = calc_native.LatexKind.Frac
    SYMBOL = LatexExpr.Frac.symbol

    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.numerator = ExpressionSlot(kind=InputKind.AUX, key="numerator", align=InputAlign.TOP)
        layout.addWidget(self.numerator, 0, Qt.AlignmentFlag.AlignHCenter)

        self.line = QFrame(self)
        self.line.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.line.setMinimumWidth(0)
        self.line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.line)

        self.denominator = ExpressionSlot(
            kind=InputKind.AUX, key="denominator", align=InputAlign.TOP
        )

        layout.addWidget(self.denominator, 0, Qt.AlignmentFlag.AlignHCenter)

        self._left_slot = self.numerator
        self._right_slot = self.denominator
        self._top_slot = self.numerator
        self._bottom_slot = self.denominator

    def anchor_y(self) -> int:
        return self.numerator.height() - self.line.height() // 2

    def focus_default(self) -> None:
        num_input = self.numerator.default_input()
        if not num_input.text():
            num_input.setFocus()
        else:
            self.denominator.default_input().setFocus()


class ScriptNode(ExpressionNode):
    """A base slot with a super/subscript hung off its right corner by geometry,
    so the script's offset stays constant at any base height.

    SCRIPT_ABOVE: the script rides above the base's glyph center, or below it.
    """

    SCRIPT_ABOVE: ClassVar[bool]
    SCRIPT_KEY: ClassVar[str]

    def __init__(self) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.base = ExpressionSlot(kind=InputKind.AUX, key="base", align=InputAlign.LEFT)
        self.script = ExpressionSlot(
            kind=InputKind.SCRIPT, key=self.SCRIPT_KEY, align=InputAlign.RIGHTT
        )
        setattr(self, self.SCRIPT_KEY, self.script)  # e.g. self.exponent / self.subscript
        self._left_slot = self.base
        self._right_slot = self.script
        self._top_slot = self.script if self.SCRIPT_ABOVE else self.base
        self._bottom_slot = self.base if self.SCRIPT_ABOVE else self.script
        for slot in (self.base, self.script):
            slot.setParent(self)
            slot.installEventFilter(self)

    def focus_default(self) -> None:
        base_input = self.base.default_input()
        if not base_input.text():
            base_input.setFocus()
        else:
            self.script.default_input().setFocus()

    def _base_glyph(self, bs: QSize) -> tuple[int, int, int]:
        """Base content right edge and vertical glyph box, stripped of QLineEdit
        chrome (autowidth pad, centering, trailing cursor slot) so the script
        hugs the glyph, not the padding."""
        base = self.base
        if not base._child_nodes:
            le = base.default_input()
            fm = le.fontMetrics()
            gh = int(fm.height())
            return int(fm.horizontalAdvance(le.text())), gh, max(0, (bs.height() - gh) // 2)
        return bs.width() - _empty_tail_w(base), bs.height(), 0

    def _script_glyph_w(self, ss: QSize) -> int:
        """Script width without its trailing cursor slot, so a script reserves no
        more room after its glyphs than a bare one does. The slot is still placed
        at full width, it is empty, so only a following sibling overlaps it, and
        typing into it drops the trim and the layout grows back."""
        return ss.width() - _empty_tail_w(self.script)

    def _geometry(self) -> tuple[QSize, QSize, int, int, int, int]:
        """(base box, script box, base right edge, script top, over_top,
        over_bottom) the vertical padding needed above/below the base box.
        script top and over_* are relative to the base box's top."""
        bs = self.base.sizeHint()
        ss = self.script.sizeHint()
        gw, gh, top_inset = self._base_glyph(bs)
        s_above, s_below = self.script.anchor_extent()
        # The script's inner edge (its bottom for a superscript, its top for a
        # subscript) hangs off the base's corner by half the base glyph. A box base
        # is not a glyph — halving it would sink the script toward the middle of a
        # tall one — so there the drop is capped by SCRIPT_DROP instead.
        drop = gh // 2
        if self.base._child_nodes:
            inner = s_below if self.SCRIPT_ABOVE else s_above
            drop = min(drop, round(SCRIPT_DROP * 2 * inner))
        script_top = (
            top_inset + drop - s_above - s_below if self.SCRIPT_ABOVE else top_inset + gh - drop
        )
        over_top = max(0, -script_top)
        over_bottom = max(0, script_top + ss.height() - bs.height())
        return bs, ss, gw, script_top, over_top, over_bottom

    def _place_script(self) -> None:
        bs, ss, gw, script_top, over_top, _ = self._geometry()
        m = self.contentsMargins()
        self.base.setGeometry(m.left(), m.top() + over_top, bs.width(), bs.height())
        self.script.setGeometry(
            m.left() + gw + SCRIPT_GAP_X,
            m.top() + over_top + script_top,
            ss.width(),
            ss.height(),
        )

    def sizeHint(self) -> QSize:
        bs, ss, gw, _, over_top, over_bottom = self._geometry()
        m = self.contentsMargins()
        content_w = max(bs.width(), gw + SCRIPT_GAP_X + self._script_glyph_w(ss))
        return QSize(
            m.left() + content_w + m.right(),
            m.top() + over_top + bs.height() + over_bottom + m.bottom(),
        )

    def minimumSizeHint(self) -> QSize:
        # No layout to derive a minimum from: the slots are placed by geometry,
        # so anything narrower than sizeHint clips them instead of reflowing.
        return self.sizeHint()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place_script()

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.LayoutRequest:
            self.updateGeometry()
            self._place_script()
        return False

    def anchor_y(self) -> int:
        # Intrinsic baseline (over_top offsets the base by the script overhang).
        _, _, _, _, over_top, _ = self._geometry()
        return over_top + self.base.anchor_y()


class PowWidget(ScriptNode):
    """UI node for power/exponent with base and exponent slots."""

    OP_ID = calc_native.OpId.Pow
    LATEX_KIND = calc_native.LatexKind.Pow
    SYMBOL = LatexExpr.Pow.symbol
    SCRIPT_ABOVE = True  # exponent hangs off the base's top-right corner
    SCRIPT_KEY = "exponent"


class SubWidget(ScriptNode):
    """UI node for a subscript with base and subscript slots."""

    LATEX_KIND = calc_native.LatexKind.Subscript
    SYMBOL = LatexExpr.Subscript.symbol
    SCRIPT_ABOVE = False  # subscript hangs off the base's bottom-right corner
    SCRIPT_KEY = "subscript"


class RootWidget(ExpressionNode):
    """UI node for root with radicand and degree slots."""

    OP_ID = calc_native.OpId.Root
    LATEX_KIND = calc_native.LatexKind.Root
    SYMBOL = LatexExpr.Root.symbol

    BORDER_WIDTH = 2
    BORDER_PADDING = 2
    DEGREE_RIGHT_MARGIN = 16

    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setAlignment(Qt.AlignmentFlag.AlignBottom)
        grid.setSpacing(0)
        grid.setVerticalSpacing(0)
        grid.setHorizontalSpacing(0)

        self.degree = ExpressionSlot(
            kind=InputKind.SCRIPT,
            key="degree",
            align=InputAlign.LEFTT,
        )

        self.degree.setContentsMargins(0, 0, self.DEGREE_RIGHT_MARGIN, 0)

        grid.addWidget(self.degree, 1, 0, 3, 1, InputAlign.LEFTB.value)

        self.sqrt_symbol = SqrtSymbol(grid)

        grid.addWidget(self.sqrt_symbol, 3, 0, 3, 4, InputAlign.RIGHT.value)
        self.radicand = ExpressionSlot(
            kind=InputKind.AUX,
            key="radicand",
            align=InputAlign.LEFTT,
        )
        grid.addWidget(self.radicand, 3, 4, 3, 2, InputAlign.RIGHTB.value)

        self.radicand.setObjectName("radicandSlot")
        self.radicand.setContentsMargins(0, self.BORDER_PADDING, 0, 0)

        self._left_slot = self.radicand
        self._right_slot = self.degree
        self._top_slot = self.degree
        self._bottom_slot = self.radicand

    def anchor_y(self) -> int:
        return (
            self.radicand.y()
            - self.contentsMargins().top()
            + self.radicand.contentsMargins().top()
            + self.radicand.anchor_y()
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
    Y_MARGIN = 6

    def __init__(
        self,
        kind: calc_native.ParenKind | None = None,
        has_open: bool = True,
        has_close: bool = True,
    ) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        self._paren_kind: calc_native.ParenKind = kind if kind is not None else self.PAREN_KIND
        self._has_open = has_open
        self._has_close = has_close

        open_sym, close_sym = paren_glyph(self._paren_kind)
        self._open_symbol: str | None = open_sym if has_open else None
        self._close_symbol: str | None = close_sym if has_close else None

        self._inner_slot = ExpressionSlot(
            kind=InputKind.AUX,
            key="innerSlot",
            align=InputAlign.TOP,
            paren=(self._open_symbol, self._close_symbol),
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, self.Y_MARGIN, 0, self.Y_MARGIN)
        layout.setSpacing(0)
        layout.addWidget(self._inner_slot, 0, Qt.AlignmentFlag.AlignHCenter)

        self._open_glyph: QWidget | None = None
        if has_open:
            self._open_glyph = self._create_open()
            if self._open_glyph is not None:
                self._inner_slot.insert_widget(0, self._open_glyph)

        self._close_glyph: QWidget | None = None
        if has_close:
            self._attach_close_glyph()

        self._left_slot = self._inner_slot

    @property
    def slot(self) -> ExpressionSlot:
        return self._inner_slot

    def _create_open(self) -> QWidget | None:
        """Return the opening glyph widget, or *None* to draw nothing."""
        return None

    def _create_close(self) -> QWidget | None:
        """Return the closing glyph widget, or *None* to draw nothing."""
        return None

    # Public API

    def set_open(self) -> None:
        """Reattach an open paren that was typed after the glyph was removed."""
        open_sym, _ = paren_glyph(self._paren_kind)
        self._open_symbol = open_sym
        self._has_open = True
        self._inner_slot._paren = (open_sym, self._close_symbol)
        if self._open_glyph is None:
            self._open_glyph = self._create_open()
            if self._open_glyph is not None:
                self._inner_slot.insert_widget(0, self._open_glyph)

    def set_close(self) -> None:
        """Attach a close paren that was typed later in a different segment."""
        _, close_sym = paren_glyph(self._paren_kind)
        self._close_symbol = close_sym
        self._has_close = True
        self._inner_slot._paren = (self._open_symbol, close_sym)
        if self._close_glyph is None:
            self._attach_close_glyph()

    def to_plain_text(self) -> str:
        return self._inner_slot.to_plain_text()

    def focus_default(self) -> None:
        le = self._inner_slot.default_input()
        if not le.text():
            le.setFocus()

    def remove(self, glyph: QWidget | None = None) -> None:
        """Remove one glyph and dissolve the ParenWidget."""
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
        if self._open_glyph is None:  # If there is no open and close glyph dissolve ParenWidget
            parent = self.parent()
            if isinstance(parent, ExpressionSlot):
                self.editor._last_focused = parent.default_input()
            self._dissolve()
        else:
            self.editor._pending_parens.setdefault(self._paren_kind, []).append(self)

    def _dissolve(self, has_node: bool = True) -> None:
        """Serialize inner content, remove this ParenWidget, write text back."""
        stack = self.editor._pending_parens.get(self._paren_kind)
        if stack and self in stack:
            stack.remove(self)
            if not stack:
                del self.editor._pending_parens[self._paren_kind]
        if has_node:
            super().dissolve()

        super().remove()

    def adopt_segments(self, segments: list[QWidget]) -> None:
        self._inner_slot.adopt_segments(segments)

    # Internal

    def _attach_close_glyph(self) -> None:
        if not self._has_close:
            return
        self._close_glyph = self._create_close()
        if self._close_glyph is not None:
            self._inner_slot.insert_widget(len(self._inner_slot._segments), self._close_glyph)

    def _detach_open_glyph(self) -> None:
        if self._open_glyph is None:
            return
        self._inner_slot._layout.removeWidget(self._open_glyph)
        self._inner_slot._segments.remove(self._open_glyph)
        self._open_glyph.deleteLater()
        self._open_glyph = None
        self._has_open = False
        self._open_symbol = None
        self._inner_slot._paren = (None, self._close_symbol)

    def _detach_close_glyph(self) -> None:
        if self._close_glyph is None:
            return
        self._inner_slot._layout.removeWidget(self._close_glyph)
        self._inner_slot._segments.remove(self._close_glyph)
        self._close_glyph.deleteLater()
        self._close_glyph = None
        self._has_close = False
        self._close_symbol = None
        self._inner_slot._paren = (self._open_symbol, None)


class BraceWidget(ParenWidget):
    """Curly-brace parenthesis: ``{ … }``."""

    PAREN_KIND = calc_native.ParenKind.Brace

    def _create_open(self) -> QWidget:
        return CurlyBrace(self._inner_slot, True)

    def _create_close(self) -> QWidget:
        return CurlyBrace(self._inner_slot, False)


class RoundParenWidget(ParenWidget):
    """Round parenthesis: ``( … )``."""

    PAREN_KIND = calc_native.ParenKind.Paren

    def _create_open(self) -> QWidget:
        return RoundParen(self._inner_slot, True)

    def _create_close(self) -> QWidget:
        return RoundParen(self._inner_slot, False)


class BracketWidget(ParenWidget):
    """Square bracket: ``[ … ]``."""

    PAREN_KIND = calc_native.ParenKind.Bracket

    def _create_open(self) -> QWidget:
        return SquareBracket(self._inner_slot, True)

    def _create_close(self) -> QWidget:
        return SquareBracket(self._inner_slot, False)
