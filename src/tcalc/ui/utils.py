#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtGui import QColor, QIcon, QPainter

# Every icon the UI shows, by file stem; bundled so no desktop icon theme is needed
ICONS_DIR = Path.cwd() / "assets" / "icons"


def rgba(hex_color: str, alpha: float) -> str:
    """Convert ``#RRGGBB`` + alpha to a CSS ``rgba(...)`` string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def split_camel(camel: str) -> str:
    """'SpeedOfLight' -> 'Speed Of Light'."""
    words = re.findall(r"[A-Z][a-z0-9]*", camel)
    return " ".join(words) if words else camel


def _apply_tint(icon: QIcon, tint: str | None) -> QIcon:
    """Return *icon* tinted with *tint* color, or unchanged if *tint* is None."""
    if tint is None or icon.isNull():
        return icon
    pm = icon.pixmap(128, 128)
    tinted = pm.copy()
    painter = QPainter(tinted)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QColor(tint))
    painter.end()
    return QIcon(tinted)


def get_icon(name: str, tint: str | None = None) -> QIcon:
    """Load ``assets/icons/<name>.svg``, tinted with *tint* if given."""
    if not name:
        return QIcon()
    return _apply_tint(QIcon(str(ICONS_DIR / f"{name}.svg")), tint)
