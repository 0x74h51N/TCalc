#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import calc_native
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from tcalc.ui.widgets.math.math_primitives import PEN_WIDTH

from .layout import LATEX_KIND_MAP, FontCache, PaintNode, Row, TextLeaf
from .widgets import ParenPaint


class MathPainter:
    def __init__(self) -> None:
        self._fm_cache = FontCache()
        self.is_painting: bool = False

    def paint_tree(self, tokenized: calc_native.TokensBranch, font: QFont) -> Row:
        root: Row = Row()
        self._emit(root, calc_native.build_math_nodes(tokenized), font)
        root.measure(self._fm_cache)
        root.place(0.0, 0.0)
        return root

    def _emit(self, row: Row, nodes: list[tuple], font: QFont) -> None:
        TEXT = calc_native.MATH_TAG_TEXT
        PAREN = calc_native.MATH_TAG_PAREN
        children = row.children
        for node in nodes:
            kind = node[0]
            if kind == TEXT:
                children.append(TextLeaf(text=node[1], font=font))
                continue
            if kind == PAREN:
                _, paren_kind, has_close, paren_children = node
                inner = Row()
                self._emit(inner, paren_children, font)
                children.append(
                    ParenPaint(
                        left=inner,
                        kind=paren_kind,
                        open_visible=True,
                        close_visible=has_close,
                    )
                )
                continue
            _, latex_kind, left_nodes, right_nodes = node
            node_cls = LATEX_KIND_MAP.get(latex_kind)
            if node_cls is None:
                continue
            left_row = Row()
            self._emit(left_row, left_nodes, font)
            right_row: Row | None = None
            if right_nodes:
                right_row = Row()
                self._emit(right_row, right_nodes, font)
            paint_node: PaintNode = node_cls(left=left_row, right=right_row)
            children.append(paint_node)


CANVAS_PAD = 4


class PaintCanvas(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tree: Row | None = None
        self._font: QFont = self.font()
        self._size = QSize(0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_tree(self, tree: Row, font: QFont) -> None:
        self._tree = tree
        self._font = font
        tree.place(0.0, CANVAS_PAD)
        self._size = QSize(int(tree.w) + 2, int(tree.h) + CANVAS_PAD * 2)
        self.setMaximumSize(self._size)
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        return self._size

    def minimumSizeHint(self) -> QSize:
        return self._size

    def paintEvent(self, _event) -> None:
        if self._tree is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.palette().windowText().color())
        pen.setWidthF(PEN_WIDTH)
        painter.setPen(pen)
        painter.setFont(self._font)
        self._tree.paint(painter)
