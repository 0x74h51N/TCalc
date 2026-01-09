from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenuBar

from tcalc.app_state import get_app_state
from tcalc.ui.controller.menubar import SettingsOperations

from ..defins import SETTINGS_ACTIONS
from ..menu_builder import MenuActionItem, ToggleMenuContext

if TYPE_CHECKING:
    from ...keyboard import ShortcutManager
    from ...window import MainWindow


class SettingsMenu:
    def __init__(self, menu: QMenuBar, window: MainWindow, shortcuts: ShortcutManager):
        self.app_state = get_app_state()
        self.window = window
        self.ops = SettingsOperations(window)
        self._mode_actions: dict = {}

        settings_menu = menu.addMenu("Settings")

        settings_ctx: ToggleMenuContext[SettingsOperations] = ToggleMenuContext(
            window,
            shortcuts,
            ops=self.ops,
            app_state=self.app_state,
        )
        for settings_item in SETTINGS_ACTIONS:
            action = settings_item.add_to(settings_menu, settings_ctx)

            if action and isinstance(settings_item, MenuActionItem) and settings_item.mode:
                self._mode_actions[settings_item.mode] = action
                action.triggered.connect(self._update_mode_selection)
        self._update_mode_selection()

    def _update_mode_selection(self) -> None:
        for mode, action in self._mode_actions.items():
            action.setChecked(mode == self.app_state.mode)
