#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from PySide6.QtGui import QColor, QIcon


def opaque_color(icon: QIcon) -> QColor:
    """Color of the first fully opaque pixel of *icon* at 32px."""
    img = icon.pixmap(32, 32).toImage()
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() == 255:
                return c
    raise AssertionError("icon has no opaque pixel")
