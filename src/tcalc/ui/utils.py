#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import re
from collections.abc import Callable
from functools import partial
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QPixmap

from tcalc.theme import Theme, get_theme, qcolor

from .config import icons_config

# Every icon the UI shows, by file stem; bundled so no desktop icon theme is needed
ICONS_DIR = Path.cwd() / "assets" / "icons"


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
    painter.fillRect(tinted.rect(), qcolor(tint))
    painter.end()
    return QIcon(tinted)


class _ThemeIconEngine(QIconEngine):
    """Draws the icon *build* makes from the active theme, rebuilt once after each switch."""

    def __init__(self, build: Callable[[], QIcon]) -> None:
        super().__init__()
        self._build = build
        self._theme: Theme | None = None
        self._icon = QIcon()

    def _current(self) -> QIcon:
        theme = get_theme()
        if theme is not self._theme:
            self._theme, self._icon = theme, self._build()
        return self._icon

    def paint(self, painter: QPainter, rect: QRect, mode: QIcon.Mode, state: QIcon.State) -> None:
        self._current().paint(painter, rect, Qt.AlignmentFlag.AlignCenter, mode, state)

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        return self._current().pixmap(size, mode, state)

    def scaledPixmap(
        self, size: QSize, mode: QIcon.Mode, state: QIcon.State, scale: float
    ) -> QPixmap:
        return self._current().pixmap(size, scale, mode, state)

    def actualSize(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QSize:
        return self._current().actualSize(size, mode, state)

    def availableSizes(
        self, mode: QIcon.Mode = QIcon.Mode.Normal, state: QIcon.State = QIcon.State.Off
    ) -> list[QSize]:
        return self._current().availableSizes(mode, state)

    def isNull(self) -> bool:
        return self._current().isNull()

    def clone(self) -> QIconEngine:
        return _ThemeIconEngine(self._build)


def theme_icon(build: Callable[[], QIcon]) -> QIcon:
    """An icon *build* makes from the active theme; it follows theme switches on its own."""
    return QIcon(_ThemeIconEngine(build))


def _load_icon(name: str, tint_key: str | None) -> QIcon:
    theme = get_theme()
    path = ICONS_DIR / theme.base / f"{name}.svg"
    if not path.exists():
        path = ICONS_DIR / f"{name}.svg"
    if tint_key is None and name not in icons_config["untinted"]:
        tint_key = "icon_color"
    return _apply_tint(QIcon(str(path)), theme.color(tint_key) if tint_key else None)


def get_icon(name: str, tint_key: str | None = None) -> QIcon:
    """Icon *name* for the active theme, tinted with the color *tint_key* uses (a
    [color_usage] name) or the icon color.

    ``assets/icons/<base>/<name>.svg`` (the theme's light/dark family) wins over ``assets/icons/<name>.svg``;
    icons in ``[icons].untinted`` keep their own colors unless *tint_key* is given.
    """
    if not name:
        return QIcon()
    return theme_icon(partial(_load_icon, name, tint_key))
