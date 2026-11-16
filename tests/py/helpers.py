#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QApplication

from tcalc.ui.widgets.calc.display.expression.expression import Expression

_editor: Expression | None = None


def opaque_color(icon: QIcon) -> QColor:
    """Color of the first fully opaque pixel of *icon* at 32px."""
    img = icon.pixmap(32, 32).toImage()
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() == 255:
                return c
    raise AssertionError("icon has no opaque pixel")


def editor_canonical(expr: str) -> str:
    """The text the controller evaluates: *expr* through the editor's widgets and back."""
    global _editor
    # Subscript has no editor widget yet; its `_{...}` form already tokenizes to its final
    # LatexToken, so it is evaluated raw instead of through a renderer that would drop it.
    if "_{" in expr:
        return expr
    app = QApplication.instance() or QApplication([])
    if _editor is None:
        _editor = Expression()
    _editor.set_plain_text(expr)
    app.processEvents()
    return _editor.get_plain_text()
