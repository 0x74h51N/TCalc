from __future__ import annotations

from PySide6.QtWidgets import QMainWindow
from .menus.file import FileMenu
from .menus.edit import EditMenu
from .menus.settings import SettingsMenu
from .style import apply_menu_styles

class Menubar:
    def __init__(self, window: QMainWindow) -> None:
        self.window = window
        self.settings_menu: SettingsMenu | None = None
        self._create_menubar()

    def _create_menubar(self) -> None:
        menubar = self.window.menuBar()

        apply_menu_styles(menubar)

        FileMenu(menubar, self.window)
        EditMenu(menubar, self.window)
        self.settings_menu = SettingsMenu(menubar, self.window)
        help_menu = menubar.addMenu("Help")
