from __future__ import annotations

from typing import TYPE_CHECKING

from ..keyboard import ShortcutManager
from .menus.edit import EditMenu
from .menus.file import FileMenu
from .menus.settings import SettingsMenu
from .style import apply_menu_styles

if TYPE_CHECKING:
    from ..window import MainWindow


class Menubar:
    def __init__(self, window: MainWindow) -> None:
        self.window = window
        self.settings_menu: SettingsMenu | None = None
        self.shortcuts = ShortcutManager()
        self._create_menubar()

    def _create_menubar(self) -> None:
        menubar = self.window.menuBar()

        apply_menu_styles(menubar)

        FileMenu(menubar, self.window, self.shortcuts)
        EditMenu(menubar, self.window, self.shortcuts)
        self.settings_menu = SettingsMenu(menubar, self.window, self.shortcuts)
        menubar.addMenu("Help")
