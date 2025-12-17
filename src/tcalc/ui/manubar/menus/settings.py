from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar, QMainWindow

from tcalc.app_state import get_app_state, CalculatorMode
from tcalc.ui.controller.menubar import SettingsOperations
from ..defins import MODE_ACTIONS, SETTINGS_TOGGLE_ACTIONS


def _get_icon(theme_name: str) -> QIcon:
    icon = QIcon.fromTheme(theme_name)
    return icon if not icon.isNull() else QIcon()


class SettingsMenu:
    def __init__(self, menu: QMenuBar, window: QMainWindow, shortcuts):
        self.app_state = get_app_state()
        self.window = window
        self.ops = SettingsOperations(window)
        
        settings_menu = menu.addMenu("Settings")

        # Mode actions
        self._mode_actions: dict[CalculatorMode, QAction] = {}
        for spec in MODE_ACTIONS:
            mode = spec["id"]
            action = QAction(_get_icon(spec["icon"]), spec["text"], window, checkable=spec["checkable"])
            action.setEnabled(spec["enabled"])
            action.triggered.connect(lambda checked, m=mode: self._set_mode(m))
            settings_menu.addAction(action)
            self._mode_actions[mode] = action
            shortcuts.bind_action(mode, action)

        self._update_mode_selection()

        settings_menu.addSeparator()

        # Visibility toggles
        toggle_checked = {
            SettingsOperations.toggle_history: self.app_state.show_history,
            SettingsOperations.toggle_constants: self.app_state.show_constant_buttons,
        }
        for spec in SETTINGS_TOGGLE_ACTIONS:
            action = QAction(_get_icon(spec["icon"]), spec["text"], window, checkable=spec["checkable"])
            action.setEnabled(spec["enabled"])
            action.setChecked(toggle_checked[spec["id"]])
            shortcuts.bind_action(spec["id"], action)
            action.triggered.connect(lambda checked, fn=spec["id"]: fn(self.ops, checked))
            settings_menu.addAction(action)

        settings_menu.addSeparator()

        # Configuration actions
        keyboard_action = QAction(
            _get_icon("input-keyboard"),
            "Configure Keyboard Shortcuts... (Coming Soon)",
            window
        )
        keyboard_action.setEnabled(False)
        settings_menu.addAction(keyboard_action)

        config_action = QAction(
            _get_icon("configure"),
            "Configure TCalc... (Coming Soon)",
            window
        )
        config_action.setEnabled(False)
        settings_menu.addAction(config_action)

    def _set_mode(self, mode: CalculatorMode) -> None:
        self.ops.set_mode(mode)
        self._update_mode_selection()

    def _update_mode_selection(self) -> None:
        for mode, action in self._mode_actions.items():
            action.setChecked(mode == self.app_state.mode)
