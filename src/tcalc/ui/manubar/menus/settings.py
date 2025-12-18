from __future__ import annotations

from typing import TYPE_CHECKING, Callable, cast

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar

from tcalc.app_state import CalculatorMode, get_app_state
from tcalc.ui.controller.menubar import SettingsOperations
from tcalc.ui.keyboard.shortcuts import ShortcutId

from ..defins import MODE_ACTIONS, SETTINGS_TOGGLE_ACTIONS

if TYPE_CHECKING:
    from ...keyboard import ShortcutManager
    from ...window import MainWindow


def _get_icon(theme_name: str) -> QIcon:
    icon = QIcon.fromTheme(theme_name)
    return icon if not icon.isNull() else QIcon()


class SettingsMenu:
    def __init__(self, menu: QMenuBar, window: MainWindow, shortcuts: ShortcutManager):
        self.app_state = get_app_state()
        self.window = window
        self.ops = SettingsOperations(window)

        settings_menu = menu.addMenu("Settings")

        # Mode actions
        self._mode_actions: dict[CalculatorMode, QAction] = {}
        for spec in MODE_ACTIONS:
            mode = spec.get("id")
            if not isinstance(mode, CalculatorMode):
                continue
            icon = _get_icon(str(spec["icon"]))
            text = str(spec["text"])
            action = QAction(icon, text, window)
            action.setCheckable(bool(spec["checkable"]))
            action.setEnabled(bool(spec["enabled"]))
            action.triggered.connect(lambda checked, m=mode: self._set_mode(m))
            settings_menu.addAction(action)
            self._mode_actions[mode] = action
            shortcuts.bind_action(mode, action)

        self._update_mode_selection()

        settings_menu.addSeparator()

        # Visibility toggles
        for spec in SETTINGS_TOGGLE_ACTIONS:
            toggle_fn = spec.get("id")
            if not callable(toggle_fn):
                continue

            icon = _get_icon(str(spec["icon"]))
            text = str(spec["text"])
            action = QAction(icon, text, window)
            action.setCheckable(bool(spec["checkable"]))
            action.setEnabled(bool(spec["enabled"]))

            toggle_callable = cast(Callable[[SettingsOperations, bool], None], toggle_fn)
            if toggle_fn is SettingsOperations.toggle_history:
                action.setChecked(bool(self.app_state.show_history))
            elif toggle_fn is SettingsOperations.toggle_constants:
                action.setChecked(bool(self.app_state.show_constant_buttons))
            else:
                action.setChecked(False)

            shortcuts.bind_action(cast(ShortcutId, toggle_fn), action)
            action.triggered.connect(lambda checked, fn=toggle_callable: fn(self.ops, checked))
            settings_menu.addAction(action)

        settings_menu.addSeparator()

        # Configuration actions
        keyboard_action = QAction(
            _get_icon("input-keyboard"), "Configure Keyboard Shortcuts... (Coming Soon)", window
        )
        keyboard_action.setEnabled(False)
        settings_menu.addAction(keyboard_action)

        config_action = QAction(_get_icon("configure"), "Configure TCalc... (Coming Soon)", window)
        config_action.setEnabled(False)
        settings_menu.addAction(config_action)

    def _set_mode(self, mode: CalculatorMode) -> None:
        self.ops.set_mode(mode)
        self._update_mode_selection()

    def _update_mode_selection(self) -> None:
        for mode, action in self._mode_actions.items():
            action.setChecked(mode == self.app_state.mode)
