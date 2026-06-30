from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenuBar

from ..defins import SETTINGS_ACTIONS
from ..menu_builder import BaseMenuContext

if TYPE_CHECKING:
    from ...keyboard import ShortcutManager
    from ...window import MainWindow


class SettingsMenu:
    def __init__(self, menu: QMenuBar, window: MainWindow, shortcuts: ShortcutManager):
        self.window = window
        self._settings_menu = menu.addMenu("Settings")
        ctx = BaseMenuContext(window, shortcuts)
        for item in SETTINGS_ACTIONS:
            item.add_to(self._settings_menu, ctx)
