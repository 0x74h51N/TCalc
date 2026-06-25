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
from PySide6.QtWidgets import QMenu

from tcalc.ui.utils import split_camel


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
            ConstEntry(spec.id, split_camel(spec.id.name), spec.symbol, spec.category)
        )
    return out


# Built once at import from the native table — no hand-maintained tables.
CONSTANTS_BY_CATEGORY: dict[calc_native.CategoryId, list[ConstEntry]] = _build()


def build_constant_menu(root: QMenu, on_select: Callable[[ConstEntry], None]) -> None:
    """Populate *root* with one submenu per category and an action per constant.
    Categories and constants are sorted A->Z.
    """
    categories = sorted(
        (cat for cat, entries in CONSTANTS_BY_CATEGORY.items() if entries),
        key=lambda cat: split_camel(cat.name).lower(),
    )
    for category in categories:
        sub = QMenu(split_camel(category.name), root)
        root.addMenu(sub)
        for entry in sorted(CONSTANTS_BY_CATEGORY[category], key=lambda e: e.name.lower()):
            action = sub.addAction(f"{entry.symbol}  {entry.name}")
            action.triggered.connect(lambda _checked=False, e=entry: on_select(e))
