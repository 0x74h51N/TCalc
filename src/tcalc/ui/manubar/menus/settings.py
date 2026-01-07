from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar

from tcalc.app_state import CalculatorMode, get_app_state
from tcalc.ui.controller.menubar import SettingsOperations

from ..defins import MODE_ACTIONS, SETTINGS_ACTIONS
from ..menu_builder import ModeMenuContext, ToggleMenuContext

if TYPE_CHECKING:
    from ...keyboard import ShortcutManager
    from ...window import MainWindow


class SettingsMenu:
    def __init__(self, menu: QMenuBar, window: MainWindow, shortcuts: ShortcutManager):
        self.app_state = get_app_state()
        self.window = window
        self.ops = SettingsOperations(window)

        settings_menu = menu.addMenu("Settings")

        # Mode actions
        self._mode_actions: dict[CalculatorMode, QAction] = {}
        mode_ctx: ModeMenuContext = ModeMenuContext(
            window, shortcuts, on_mode_selected=self._set_mode
        )
        for mode_item in MODE_ACTIONS:
            action = mode_item.add_to(settings_menu, mode_ctx)
            if action is not None:
                self._mode_actions[mode_item.mode] = action

        self._update_mode_selection()

        settings_menu.addSeparator()

        # Settings actions (toggles + config placeholders)
        settings_ctx: ToggleMenuContext[SettingsOperations] = ToggleMenuContext(
            window,
            shortcuts,
            ops=self.ops,
            app_state=self.app_state,
        )
        for settings_item in SETTINGS_ACTIONS:
            settings_item.add_to(settings_menu, settings_ctx)

    def _set_mode(self, mode: CalculatorMode) -> None:
        self.ops.set_mode(mode)
        self._update_mode_selection()

    def _update_mode_selection(self) -> None:
        for mode, action in self._mode_actions.items():
            action.setChecked(mode == self.app_state.mode)
