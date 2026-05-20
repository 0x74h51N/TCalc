#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Concrete PaintNode subclasses: FractionPaint, PowPaint, RootPaint, ParenPaint.
# Each owns its measure/place/paint logic. Mirrors widgets.py on the editor side.

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import calc_native
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainter, QPainterPath

from ..math_primitives import (
    PEN_WIDTH,
    SQRT_LEFT_RATIO,
    SQRT_WIDTH,
    curly_brace_path,
    round_paren_path,
    sqrt_path,
    square_bracket_path,
)
from .layout import (
    FRACTION_PAD_X,
    FRACTION_PAD_Y,
    LATEX_KIND_MAP,
    PAREN_GLYPH_W,
    PAREN_X_PAD,
    PAREN_Y_MARGIN,
    PAREN_Y_PAD,
    POW_OVERLAP,
    ROOT_OVERLINE_PAD,
    SCRIPT_SCALE,
    PaintNode,
)

if TYPE_CHECKING:
    from .layout import FontCache, Row


def _stroke_path(painter: QPainter, path: QPainterPath, x: float, y: float) -> None:
    painter.translate(x, y)
    painter.drawPath(path)
    painter.translate(-x, -y)


class FractionPaint(PaintNode):
    LATEX_KIND = calc_native.LatexKind.Frac

    def measure(self, fm_cache: FontCache, scale: float = 1.0) -> None:
        if self.right is None:
            return
        self.left.measure(fm_cache, scale)
        self.right.measure(fm_cache, scale)
        inner_w = max(self.left.w, self.right.w) + FRACTION_PAD_X * 2
        self.w = inner_w
        self.h = self.left.h + PEN_WIDTH + FRACTION_PAD_Y * 2 + self.right.h
        self.above = self.left.h + FRACTION_PAD_Y + PEN_WIDTH / 2.0
        self.below = self.h - self.above

    def place(self, x: float, y: float) -> None:
        super().place(x, y)
        tx = x + (self.w - self.left.w) / 2.0
        self.left.place(tx, y + FRACTION_PAD_Y)
        if self.right is not None:
            bx = x + (self.w - self.right.w) / 2.0
            self.right.place(bx, y + self.left.h + PEN_WIDTH + FRACTION_PAD_Y)

    def paint(self, painter: QPainter) -> None:
        super().paint(painter)
        bar_y = self.y + self.left.h + FRACTION_PAD_Y + PEN_WIDTH / 2.0
        painter.drawLine(QPointF(self.x, bar_y), QPointF(self.x + self.w, bar_y))


class PowPaint(PaintNode):
    LATEX_KIND = calc_native.LatexKind.Pow

    def measure(self, fm_cache: FontCache, scale: float = 1.0) -> None:
        if self.right is None:
            return
        self.left.measure(fm_cache, scale)
        self.right.measure(fm_cache, scale * SCRIPT_SCALE)
        raise_amt = self.left.above * (1.0 - POW_OVERLAP) + self.right.h * POW_OVERLAP
        self.w = self.left.w + self.right.w
        self.above = self.left.above + max(0.0, self.right.h - raise_amt + self.right.below)
        self.below = self.left.below
        self.h = self.above + self.below

    def place(self, x: float, y: float) -> None:
        super().place(x, y)
        if self.right is None:
            return
        base_y = y + self.above - self.left.above
        self.left.place(x, base_y)
        exp_x = x + self.left.w
        exp_y = y + self.above - self.left.above - self.right.below
        self.right.place(exp_x, exp_y)


class RootPaint(PaintNode):
    LATEX_KIND = calc_native.LatexKind.Root
    GLYPH_W = SQRT_WIDTH

    def measure(self, fm_cache: FontCache, scale: float = 1.0) -> None:
        self.left.measure(fm_cache, scale)

        if self.right is not None:
            self.right.measure(fm_cache, scale * SCRIPT_SCALE)

        radicand_h = self.left.h + PEN_WIDTH + ROOT_OVERLINE_PAD
        self.glyph_w = self.GLYPH_W

        index_w = self.right.w if self.right is not None else 0.0
        self.w = index_w + self.glyph_w + self.left.w
        index_bump = 0.0

        if self.right is not None:
            glyph_left_offset = radicand_h * SQRT_LEFT_RATIO
            degree_above_radicand_top = self.right.h + ROOT_OVERLINE_PAD - glyph_left_offset
            index_bump = max(0.0, degree_above_radicand_top)

        self.h = radicand_h + index_bump
        self.above = index_bump + PEN_WIDTH + ROOT_OVERLINE_PAD + self.left.above
        self.below = self.h - self.above

    def place(self, x: float, y: float) -> None:
        super().place(x, y)
        idx_w = 0.0
        radicand_top = y + self.above - self.left.above - ROOT_OVERLINE_PAD - PEN_WIDTH
        radicand_h = self.left.h + PEN_WIDTH + ROOT_OVERLINE_PAD
        radicand_y = radicand_top + PEN_WIDTH + ROOT_OVERLINE_PAD
        if self.right is not None:
            glyph_left_y = radicand_top + radicand_h * SQRT_LEFT_RATIO
            degree_y = glyph_left_y - self.right.h
            self.right.place(x + 2 * ROOT_OVERLINE_PAD, degree_y)
            idx_w = self.right.w
        self.left.place(x + idx_w + self.glyph_w, radicand_y)

    def paint(self, painter):
        super().paint(painter)
        radicand_top = self.left.y - ROOT_OVERLINE_PAD - PEN_WIDTH
        radicand_h = self.left.h + PEN_WIDTH + ROOT_OVERLINE_PAD
        glyph_x = self.left.x - self.glyph_w
        _stroke_path(painter, sqrt_path(self.glyph_w, radicand_h), glyph_x, radicand_top)
        painter.drawLine(
            QPointF(self.left.x + ROOT_OVERLINE_PAD // 2, radicand_top),
            QPointF(self.left.x + self.left.w, radicand_top),
        )


_PAREN_PATH: dict[calc_native.ParenKind, Callable[[float, float, bool], QPainterPath]] = {
    calc_native.ParenKind.Paren: round_paren_path,
    calc_native.ParenKind.Bracket: square_bracket_path,
    calc_native.ParenKind.Brace: curly_brace_path,
}


class ParenPaint(PaintNode):
    def __init__(
        self,
        left: Row,
        right: Row | None = None,
        kind: calc_native.ParenKind = calc_native.ParenKind.Paren,
        open_visible: bool = True,
        close_visible: bool = True,
    ) -> None:
        super().__init__(left=left, right=right)
        self.kind = kind
        self.open_visible = open_visible
        self.close_visible = close_visible

    def measure(self, fm_cache: FontCache, scale: float = 1.0) -> None:
        self.left.measure(fm_cache, scale)
        gw = PAREN_GLYPH_W.get(self.kind, 0.0)

        self.glyph_w = gw
        lw = (gw + PAREN_X_PAD) if self.open_visible else 0.0
        rw = (gw + PAREN_X_PAD) if self.close_visible else 0.0
        self.glyph_h = self.left.h + 2 * PAREN_Y_PAD
        self.w = lw + self.left.w + rw
        self.h = self.glyph_h + 2 * PAREN_Y_MARGIN
        self.above = self.h / 2.0
        self.below = self.h / 2.0

    def place(self, x: float, y: float) -> None:
        super().place(x, y)
        lw = (self.glyph_w + PAREN_X_PAD) if self.open_visible else 0.0
        self.left.place(x + lw, y + PAREN_Y_MARGIN + PAREN_Y_PAD)

    def paint(self, painter: QPainter) -> None:
        self.left.paint(painter)

        builder = _PAREN_PATH[self.kind]
        path = builder(self.glyph_w, self.glyph_h, True)
        glyph_y = self.y + PAREN_Y_MARGIN
        if self.open_visible:
            _stroke_path(painter, path, self.x, glyph_y)
        if self.close_visible:
            painter.save()
            painter.translate(self.x + self.w, glyph_y)
            painter.scale(-1, 1)
            painter.drawPath(path)
            painter.restore()


LATEX_KIND_MAP.update(
    {
        calc_native.LatexKind.Frac: FractionPaint,
        calc_native.LatexKind.Pow: PowPaint,
        calc_native.LatexKind.Root: RootPaint,
    }
)
