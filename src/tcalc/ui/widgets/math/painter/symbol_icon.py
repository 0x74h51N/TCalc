#
# TCalc - Copyright (C) 2026 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)

from tcalc.core.constants import strip_subscript

from ..math_primitives import PEN_WIDTH

_PAD = 2
_SUB_SCALE = 0.7
_BASE_RATIO = 0.72  # base-letter height as a fraction of the icon box height
_cache: dict[tuple, QIcon] = {}
ICON_BOX = QSize(22, 22)


def needs_math_render(symbol: str) -> bool:
    return "_{" in symbol


def _dpr() -> float:
    screen = QGuiApplication.primaryScreen()
    return screen.devicePixelRatio() if screen is not None else 1.0


def render_symbol(symbol: str, color: QColor, box: QSize) -> QIcon:
    """Draw a constant symbol (plain, or `base_{sub}`) into *box*: base at ~72% of the
    box height, subscript smaller and dropped, left-aligned and vertically centered.
    Constant symbols never nest, so this is plain drawText — no tokenize/paint_tree."""
    dpr = _dpr()
    key = (symbol, color.rgba(), box.width(), box.height(), dpr)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    px = max(1, int(box.height() * _BASE_RATIO))
    base_font = QFont()
    base_font.setPixelSize(px)
    sub_font = QFont(base_font)
    sub_font.setPixelSize(max(1, int(px * _SUB_SCALE)))
    pix = QPixmap(int(box.width() * dpr), int(box.height() * dpr))
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(color, PEN_WIDTH))
    fm = QFontMetrics(base_font)
    base, _, sub = strip_subscript(symbol).partition("_")
    baseline = (box.height() + fm.ascent() - fm.descent()) / 2.0
    painter.setFont(base_font)
    painter.drawText(QPointF(float(_PAD), baseline), base)
    if sub:
        painter.setFont(sub_font)
        painter.drawText(
            QPointF(float(_PAD + fm.horizontalAdvance(base)), baseline + fm.descent()), sub
        )
    painter.end()
    icon = QIcon(pix)
    _cache[key] = icon
    return icon
