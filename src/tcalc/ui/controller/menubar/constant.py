#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from typing import TYPE_CHECKING

from tcalc.ui.widgets.common.constants_menu import ConstEntry

if TYPE_CHECKING:
    from ...window import MainWindow


class ConstantOperations:
    def __init__(self, window: MainWindow) -> None:
        self.window = window

    def insert(self, entry: ConstEntry) -> None:
        self.window.calc_widget.display.editor.insert_text(entry.symbol)
