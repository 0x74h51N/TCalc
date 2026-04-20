#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from collections import deque

import calc_native
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from tcalc.ui.widgets.math.math_primitives import PEN_WIDTH
from tcalc.ui.widgets.math.utils import ExprSplit, ParenSplit, structural_split

from .layout import EXPR_KIND_MAP, FontCache, PaintNode, Row, TextLeaf
from .widgets import ParenPaint

PendingQueue = deque[tuple[Row, calc_native.TokenizeResult]]


class MathPainter:
    def __init__(self) -> None:
        self._fm_cache = FontCache()
        self.is_painting: bool = False

    def paint_tree(self, tokenized: calc_native.TokenizeResult, font: QFont) -> Row:
        root: Row = Row()
        pending: PendingQueue = deque()

        if tokenized.expr_indices:
            pending.append((root, tokenized))
        else:
            root.children.append(
                TextLeaf(text=calc_native.tokens_to_text(list(tokenized.tokens)), font=font)
            )

        while pending:
            row, tok_result = pending.popleft()
            tokens = list(tok_result.tokens)

            split = structural_split(tokens, tok_result)
            if split is None:
                row.children.append(TextLeaf(text=calc_native.tokens_to_text(tokens), font=font))
                continue

            if split.prefix:
                row.children.append(
                    TextLeaf(text=calc_native.tokens_to_text(split.prefix), font=font)
                )

            node: PaintNode
            if isinstance(split, ParenSplit):
                inner_row = Row()
                node = ParenPaint(
                    left=inner_row,
                    kind=split.open_tok.kind,
                    open_visible=True,
                    close_visible=split.has_close,
                )
                self._paint_node(row, node, split.left, None, font, pending)
            else:
                assert isinstance(split, ExprSplit)
                node_cls = EXPR_KIND_MAP.get(split.kind)
                if node_cls is None:
                    row.children.append(
                        TextLeaf(text=calc_native.tokens_to_text(tokens), font=font)
                    )
                    continue
                left_row = Row()
                right_row = Row() if split.right else None
                node = node_cls(left=left_row, right=right_row)
                self._paint_node(row, node, split.left, split.right, font, pending)

            if split.suffix:
                self._enqueue(row, split.suffix, font, pending)

        root.measure(self._fm_cache)
        root.place(0.0, 0.0)
        return root

    def _enqueue(
        self,
        row: Row,
        tokens: list[calc_native.Token],
        font: QFont,
        pending: PendingQueue,
    ) -> None:
        if not tokens:
            return
        classified = calc_native.classify_tokens(tokens)
        if classified.expr_indices:
            pending.append((row, classified))
        else:
            row.children.append(TextLeaf(text=calc_native.tokens_to_text(tokens), font=font))

    def _paint_node(
        self,
        row: Row,
        node: PaintNode,
        left_tokens: list[calc_native.Token],
        right_tokens: list[calc_native.Token] | None,
        font: QFont,
        pending: PendingQueue,
    ) -> None:
        row.children.append(node)
        if node.left is not None:
            self._enqueue(node.left, left_tokens, font, pending)
        if node.right is not None and right_tokens:
            self._enqueue(node.right, right_tokens, font, pending)


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
