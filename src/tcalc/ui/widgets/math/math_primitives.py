#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QSizePolicy, QWidget

SQRT_WIDTH = 25
SQRT_LEFT_RATIO = 0.35
ROUND_PAREN_WIDTH = 8
SQUARE_BRACKET_WIDTH = 8
CURLY_BRACE_WIDTH = 12
PEN_WIDTH = 2


@dataclass(frozen=True)
class ScriptNudge:
    """Pixel fine-tuning of a script's position relative to its base corner
    (x: + right, y: + down). Shared by the paint and widget renderers so both
    sit the same."""

    x: int = 0
    y: int = 0


POW_SCRIPT_NUDGE = ScriptNudge(x=1, y=7)  # exponent nudged down toward the base
SUB_SCRIPT_NUDGE = ScriptNudge(x=1, y=-4)  # subscript nudged up toward the base


def sqrt_path(w: float, h: float) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0, h * SQRT_LEFT_RATIO)
    path.lineTo(w * 0.25, h * SQRT_LEFT_RATIO)
    path.lineTo(w * 0.45, h)
    path.lineTo(w, 0)
    return path


def _mirror(path: QPainterPath, w: float) -> QPainterPath:
    return QTransform(-1, 0, 0, 1, w, 0).map(path)


def curly_brace_path(w: float, h: float, opening: bool) -> QPainterPath:
    mid_y = h / 2
    r = min(w * 0.8, h * 0.15)
    path = QPainterPath()
    path.moveTo(w, 0)
    path.quadTo(w * 0.3, 0, w * 0.3, r)
    path.lineTo(w * 0.3, mid_y - r)
    path.quadTo(w * 0.3, mid_y, 0, mid_y)
    path.quadTo(w * 0.3, mid_y, w * 0.3, mid_y + r)
    path.lineTo(w * 0.3, h - r)
    path.quadTo(w * 0.3, h, w, h)
    return path if opening else _mirror(path, w)


def round_paren_path(w: float, h: float, opening: bool) -> QPainterPath:
    p = PEN_WIDTH
    path = QPainterPath()
    path.moveTo(w, 0)
    path.quadTo(p, h * 0.25, p, h * 0.5)
    path.quadTo(p, h * 0.75, w, h)
    return path if opening else _mirror(path, w)


def square_bracket_path(w: float, h: float, opening: bool) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(w, 0)
    path.lineTo(w * 0.3, 0)
    path.lineTo(w * 0.3, h)
    path.lineTo(w, h)
    return path if opening else _mirror(path, w)


class MathPrimitive(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = Qt.GlobalColor.white
        self._pen_width = 2.0

    def setColor(self, color):
        self._color = color
        self.update()

    def setPenWidth(self, width: float):
        self._pen_width = width
        self.update()

    def build_path(self, w: float, h: float) -> QPainterPath:
        raise NotImplementedError

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._color)
        pen.setWidthF(self._pen_width)
        painter.setPen(pen)
        path = self.build_path(float(self.width()), float(self.height()))
        painter.drawPath(path)


class SqrtSymbol(MathPrimitive):
    WIDTH = SQRT_WIDTH

    def __init__(self, parent=None):
        super().__init__()
        self.setMinimumWidth(self.WIDTH)
        self._pen_width = 2.0

    def build_path(self, w: float, h: float) -> QPainterPath:
        return sqrt_path(w, h)


class ParenGlyph(MathPrimitive):
    WIDTH = 10

    def __init__(self, parent: QWidget | None, opening: bool) -> None:
        super().__init__(parent)
        self._opening = opening
        self._pen_width = PEN_WIDTH
        self.setFixedWidth(self.WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def _build(self, w: float, h: float) -> QPainterPath:
        raise NotImplementedError

    def build_path(self, w: float, h: float) -> QPainterPath:
        path = self._build(w, h)
        if not self._opening:
            path = _mirror(path, w)
        return path


class CurlyBrace(ParenGlyph):
    WIDTH = CURLY_BRACE_WIDTH

    def _build(self, w: float, h: float) -> QPainterPath:
        return curly_brace_path(w, h, True)


class RoundParen(ParenGlyph):
    WIDTH = ROUND_PAREN_WIDTH

    def _build(self, w: float, h: float) -> QPainterPath:
        return round_paren_path(w, h, True)


class SquareBracket(ParenGlyph):
    WIDTH = SQUARE_BRACKET_WIDTH

    def _build(self, w: float, h: float) -> QPainterPath:
        return square_bracket_path(w, h, True)
