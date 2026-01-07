from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenuBar

from tcalc.ui.controller.menubar import FileOperations

from ..defins import FILE_MENU_ACTIONS
from ..menu_builder import OpsMenuContext

if TYPE_CHECKING:
    from ...keyboard import ShortcutManager
    from ...window import MainWindow


class FileMenu:
    def __init__(self, menu: QMenuBar, window: MainWindow, shortcuts: ShortcutManager):
        self.ops = FileOperations(window)

        file_menu = menu.addMenu("File")

        ctx: OpsMenuContext[FileOperations] = OpsMenuContext(
            window=window, shortcuts=shortcuts, ops=self.ops
        )
        for item in FILE_MENU_ACTIONS:
            item.add_to(file_menu, ctx)
