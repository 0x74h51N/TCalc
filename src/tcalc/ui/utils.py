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

from tcalc.theme import get_theme

from .config import icons_config

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
    """Load *name* for the active theme, tinted with *tint* or the theme's icon color.

    ``assets/icons/<variant>/<name>.svg`` wins over ``assets/icons/<name>.svg``;
    icons in ``[icons].untinted`` keep their own colors unless *tint* is given.
    """
    if not name:
        return QIcon()
    theme = get_theme()
    path = ICONS_DIR / theme.variant / f"{name}.svg"
    if not path.exists():
        path = ICONS_DIR / f"{name}.svg"
    if tint is None and name not in icons_config["untinted"]:
        tint = theme.colors["icon"]
    return _apply_tint(QIcon(str(path)), tint)
