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

ASSETS_DIR = Path.cwd() / "assets"


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


def get_icon(icon_ref: str, tint: str | None = None) -> QIcon:
    if not icon_ref:
        return QIcon()

    if icon_ref.startswith(":/"):
        icon = QIcon(icon_ref)
        return _apply_tint(icon, tint) if not icon.isNull() else QIcon()

    path = Path(icon_ref)

    if path.suffix.lower() in {".svg", ".png", ".jpg", ".jpeg", ".ico"}:
        if not path.is_absolute():
            path = ASSETS_DIR / path.name
        icon = QIcon(str(path))
        return _apply_tint(icon, tint) if not icon.isNull() else QIcon()

    icon = QIcon.fromTheme(icon_ref)
    return _apply_tint(icon, tint) if not icon.isNull() else QIcon()
