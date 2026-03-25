from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenuBar

from tcalc.app_state import get_app_state
from tcalc.ui.controller.menubar import SettingsOperations

from ..defins import SETTINGS_ACTIONS
from ..menu_builder import MenuActionType, ToggleMenuContext

if TYPE_CHECKING:
    from PySide6.QtGui import QAction

    from ...keyboard import ShortcutManager
    from ...window import MainWindow


class SettingsMenu:
    def __init__(self, menu: QMenuBar, window: MainWindow, shortcuts: ShortcutManager):
        self.app_state = get_app_state()
        self.window = window
        self.ops = SettingsOperations(window)
        self._mode_actions: dict = {}
        self._toggle_actions: dict[str, QAction] = {}

        settings_menu = menu.addMenu("Settings")

        ctx: ToggleMenuContext[SettingsOperations] = ToggleMenuContext(
            window,
            shortcuts,
            ops=self.ops,
            app_state=self.app_state,
        )

        for item in SETTINGS_ACTIONS:
            for defn, action in item.add_to(settings_menu, ctx):
                if defn.mode:
                    self._mode_actions[defn.mode] = action
                    action.triggered.connect(self._update_mode_selection)
                if defn.item_type == MenuActionType.TOGGLE and defn.checked_attr:
                    self._toggle_actions[defn.checked_attr] = action

        self._update_mode_selection()

    def _update_mode_selection(self) -> None:
        for mode, action in self._mode_actions.items():
            action.setChecked(mode == self.app_state.mode)

    def sync_toggle(self, attr: str, value: bool) -> None:
        action = self._toggle_actions.get(attr)
        if action is None:
            return
        if action.isChecked() == value:
            return
        action.blockSignals(True)
        action.setChecked(value)
        action.blockSignals(False)
