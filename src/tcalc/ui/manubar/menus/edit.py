from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenuBar

from tcalc.ui.controller.menubar import EditOperations

from ..defins import EDIT_MENU_ACTIONS
from ..menu_builder import OpsMenuContext

if TYPE_CHECKING:
    from ...keyboard import ShortcutManager
    from ...window import MainWindow


class EditMenu:
    def __init__(self, menu: QMenuBar, window: MainWindow, shortcuts: ShortcutManager):
        self.window = window
        self.edit_ops = EditOperations(window)

        edit_menu = menu.addMenu("Edit")

        ctx: OpsMenuContext[EditOperations] = OpsMenuContext(
            window=window, shortcuts=shortcuts, ops=self.edit_ops
        )
        for item in EDIT_MENU_ACTIONS:
            item.add_to(edit_menu, ctx)
