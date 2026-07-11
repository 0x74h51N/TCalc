#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import calc_native
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMenu, QProxyStyle, QStyle

from tcalc.core.constants import CONST_NAMES
from tcalc.theme import get_theme
from tcalc.ui.utils import split_camel
from tcalc.ui.widgets.math.painter.symbol_icon import ICON_BOX, render_symbol


class _ConstIconStyle(QProxyStyle):
    """Enlarge a menu's icon column so the fixed-size constant icons aren't downscaled."""

    def pixelMetric(self, metric, option=None, widget=None):  # noqa: N802
        if metric == QStyle.PixelMetric.PM_SmallIconSize:
            return max(ICON_BOX.width(), ICON_BOX.height())
        return super().pixelMetric(metric, option, widget)


@dataclass(frozen=True, slots=True)
class ConstEntry:
    id: calc_native.ConstId
    name: str
    symbol: str
    category: calc_native.CategoryId


def _build() -> dict[calc_native.CategoryId, list[ConstEntry]]:
    out: dict[calc_native.CategoryId, list[ConstEntry]] = {}
    for spec in calc_native.const_table():
        out.setdefault(spec.category, []).append(
            ConstEntry(spec.id, CONST_NAMES[spec.id], spec.symbol, spec.category)
        )
    return out


# Built once at import from the native table — no hand-maintained tables.
CONSTANTS_BY_CATEGORY: dict[calc_native.CategoryId, list[ConstEntry]] = _build()


def build_constant_menu(root: QMenu, on_select: Callable[[ConstEntry], None]) -> None:
    """Populate *root* with one submenu per category and an action per constant.
    Every symbol is a uniform, left-aligned icon so subscript and plain symbols align."""
    color = QColor(get_theme().colors["text_primary"])
    style = _ConstIconStyle()
    style.setParent(root)
    root.setStyle(style)

    categories = sorted(
        (cat for cat, group in CONSTANTS_BY_CATEGORY.items() if group),
        key=lambda cat: split_camel(cat.name).lower(),
    )
    for category in categories:
        sub = QMenu(split_camel(category.name), root)
        sub.setStyle(style)
        root.addMenu(sub)
        for entry in sorted(CONSTANTS_BY_CATEGORY[category], key=lambda e: e.name.lower()):
            icon = render_symbol(entry.symbol, color, ICON_BOX)
            action = sub.addAction(icon, entry.name)
            action.triggered.connect(lambda _checked=False, e=entry: on_select(e))
