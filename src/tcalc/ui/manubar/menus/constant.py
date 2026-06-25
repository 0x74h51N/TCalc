#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu, QMenuBar

from tcalc.ui.controller.menubar import ConstantOperations
from tcalc.ui.widgets.common.constants_menu import build_constant_menu

if TYPE_CHECKING:
    from ...window import MainWindow


class ConstantMenu:
    def __init__(self, menu: QMenuBar, window: MainWindow) -> None:
        self.window = window
        self.ops = ConstantOperations(window)
        const_menu = QMenu("Constants", menu)
        menu.addMenu(const_menu)
        build_constant_menu(const_menu, self.ops.insert)
