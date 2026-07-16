#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

import calc_native
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QFontMetricsF, QPainter

from ..math_primitives import (
    CURLY_BRACE_WIDTH,
    ROUND_PAREN_WIDTH,
    SCRIPT_SCALES,
    SQUARE_BRACKET_WIDTH,
)

FRACTION_PAD_X = 2
FRACTION_PAD_Y = 2
ROOT_OVERLINE_PAD = 2
PAREN_X_PAD = 6
PAREN_Y_PAD = 2
PAREN_Y_MARGIN = 6

PAREN_GLYPH_W: dict[calc_native.ParenKind, float] = {
    calc_native.ParenKind.Brace: CURLY_BRACE_WIDTH,
    calc_native.ParenKind.Paren: ROUND_PAREN_WIDTH,
    calc_native.ParenKind.Bracket: SQUARE_BRACKET_WIDTH,
}


class FontCache:
    def __init__(self) -> None:
        self._cache: dict[tuple, QFontMetricsF] = {}

    def metrics(self, font: QFont) -> QFontMetricsF:
        key = (font.family(), font.pointSizeF(), font.pixelSize(), font.weight(), font.italic())
        fm = self._cache.get(key)
        if fm is None:
            fm = QFontMetricsF(font)
            self._cache[key] = fm
        return fm


def scaled_font(font: QFont, scale: float) -> QFont:
    if scale == 1.0:
        return font
    f = QFont(font)
    px = f.pixelSize()
    if px > 0:
        f.setPixelSize(max(1, int(round(px * scale))))
    else:
        f.setPointSizeF(max(1.0, f.pointSizeF() * scale))
    return f


@dataclass
class LayoutBox:
    w: float = 0.0
    h: float = 0.0
    above: float = 0.0
    below: float = 0.0
    x: float = 0.0
    y: float = 0.0

    def measure(self, fm_cache: FontCache, level: int = 0) -> None:
        pass

    def place(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def paint(self, painter: QPainter) -> None:
        pass


@dataclass
class TextLeaf(LayoutBox):
    text: str = ""
    font: QFont | None = None

    def measure(self, fm_cache: FontCache, level: int = 0) -> None:
        if self.font is None:
            return
        effective = scaled_font(self.font, SCRIPT_SCALES[level])
        self.font = effective
        fm = fm_cache.metrics(effective)
        self.w = fm.horizontalAdvance(self.text) if self.text else 0.0
        self.h = fm.height()
        self.above = self.h / 2.0
        self.below = self.h - self.above

    def paint(self, painter: QPainter) -> None:
        if not self.text or self.font is None:
            return
        painter.setFont(self.font)
        rect = QRectF(self.x, self.y, self.w, self.h)
        flags = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        painter.drawText(rect, flags, self.text)


@dataclass
class Row(LayoutBox):
    children: list[LayoutBox] = field(default_factory=list)

    def measure(self, fm_cache: FontCache, level: int = 0) -> None:
        if not self.children:
            return
        for c in self.children:
            c.measure(fm_cache, level)
        self.above = max(c.above for c in self.children)
        self.below = max(c.below for c in self.children)
        self.h = self.above + self.below
        self.w = sum(c.w for c in self.children)

    def place(self, x: float, y: float) -> None:
        super().place(x, y)
        cx = x
        for c in self.children:
            cy = y + (self.above - c.above)
            c.place(cx, cy)
            cx += c.w

    def paint(self, painter: QPainter) -> None:
        for c in self.children:
            c.paint(painter)


@dataclass
class PaintNode(LayoutBox):
    left: Row = field(default_factory=Row)
    right: Row | None = None
    glyph_w: float = 0.0

    LATEX_KIND: ClassVar[calc_native.LatexKind]

    def measure(self, fm_cache: FontCache, level: int = 0) -> None:
        pass

    def place(self, x: float, y: float) -> None:
        super().place(x, y)

    def paint(self, painter: QPainter) -> None:
        self.left.paint(painter)
        if self.right is not None:
            self.right.paint(painter)


LATEX_KIND_MAP: dict[calc_native.LatexKind, type[PaintNode]] = {}
