#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""probe paint: the painter's boxes for a text, as a history item paints it in math mode."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from probes.app import save_png, settle, styled_app
from probes.options import Options, read_inputs
from probes.rows import Layer, ProbeError, Row, format_rows
from tcalc.core.parser import tokenize
from tcalc.theme import get_theme
from tcalc.ui.widgets.math.painter.layout import LayoutBox, PaintNode, TextLeaf
from tcalc.ui.widgets.math.painter.layout import Row as BoxRow
from tcalc.ui.widgets.math.painter.math_painter import MathPainter, PaintCanvas

INDENT = "  "


def _children(box: LayoutBox) -> list[LayoutBox]:
    match box:
        case BoxRow():
            return list(box.children)
        case PaintNode():
            return [box.left, *([box.right] if box.right is not None else [])]
        case TextLeaf():
            return []
        case _:
            raise ProbeError(f"no children known for a {type(box).__name__}")


def _geometry(box: LayoutBox) -> str:
    numbers = " ".join(f"{n:g}" for n in (box.x, box.y, box.w, box.h, box.above, box.below))
    return f"{numbers} {box.text!r}" if isinstance(box, TextLeaf) else numbers


def _box_rows(text: str, box: LayoutBox, depth: int) -> list[Row]:
    """The box, then its children depth first; the type column is the class, indented by depth."""
    row = Row(text, Layer.PAINT, INDENT * depth + type(box).__name__, _geometry(box))
    return [row, *(r for child in _children(box) for r in _box_rows(text, child, depth + 1))]


def history_font() -> QFont:
    """The font a history item paints its math in (HistoryItem._math_paint)."""
    font = QFont(QApplication.font())
    font.setPointSize(get_theme().look.history.math_font_size)
    return font


def paint_canvas(text: str) -> tuple[PaintCanvas, list[Row]]:
    """The text's box tree placed on a canvas, as set_tree places it, and a row per box."""
    font = history_font()
    tree = MathPainter().paint_tree(tokenize(text), font)
    canvas = PaintCanvas()
    # set_tree places the boxes at once; only a picture needs the canvas shown
    canvas.set_tree(tree, font)
    return canvas, _box_rows(text, tree, 0)


def run(options: Options) -> int:
    with styled_app(options.theme):
        painted = [paint_canvas(one.text) for one in read_inputs(options, grouped=False)]
        if options.png is not None and painted:
            canvas = painted[-1][0]
            canvas.show()
            settle()
            save_png(canvas, options.png)
    print(format_rows([row for _, rows in painted for row in rows]), end="")
    return 0
