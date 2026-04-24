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

    def _emit(self, row: Row, nodes: list[calc_native.MathNode], font: QFont) -> None:
        for node in nodes:
            kind = node.kind
            if kind == calc_native.MathNodeKind.Text:
                row.children.append(TextLeaf(text=node.as_text().text, font=font))
                continue
            if kind == calc_native.MathNodeKind.Paren:
                paren = node.as_paren()
                inner = Row()
                self._emit(inner, paren.children, font)
                row.children.append(
                    ParenPaint(
                        left=inner,
                        kind=paren.kind,
                        open_visible=True,
                        close_visible=paren.has_close,
                    )
                )
                continue
            latex = node.as_latex()
            node_cls = LATEX_KIND_MAP.get(latex.kind)
            if node_cls is None:
                continue
            left_row = Row()
            self._emit(left_row, latex.left, font)
            right_row: Row | None = None
            if latex.right:
                right_row = Row()
                self._emit(right_row, latex.right, font)
            paint_node: PaintNode = node_cls(left=left_row, right=right_row)
            row.children.append(paint_node)


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
