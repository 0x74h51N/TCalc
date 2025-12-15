from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar, QMainWindow

from ....app_state import get_app_state, CalculatorMode


def _get_icon(theme_name: str) -> QIcon:
    icon = QIcon.fromTheme(theme_name)
    return icon if not icon.isNull() else QIcon()


class SettingsMenu:

    # mode, icon, label, enabled
    _MODE_CONFIG = [
        (CalculatorMode.SIMPLE, "accessories-calculator", "Simple Mode", True),
        (CalculatorMode.SCIENCE, "applications-science", "Science Mode (Coming Soon)", True),
        (CalculatorMode.STATISTIC, "office-chart-bar", "Statistic Mode (Coming Soon)", False),
    ]

    def __init__(self, menu: QMenuBar, window: QMainWindow):
        self.app_state = get_app_state()
        self.window = window
        
        settings_menu = menu.addMenu("Settings")
        
        # Mode actions
        self._mode_actions: dict[CalculatorMode, QAction] = {}
        for mode, icon, label, enabled in self._MODE_CONFIG:
            action = QAction(_get_icon(icon), label, window, checkable=True)
            action.setEnabled(enabled)
            action.triggered.connect(lambda checked, m=mode: self._set_mode(m))
            settings_menu.addAction(action)
            self._mode_actions[mode] = action
        
        self._update_mode_selection()
        
        settings_menu.addSeparator()
        
        # Visibility toggles
        self.history_action = QAction(
            _get_icon("view-history"),
            "Show History",
            window,
            checkable=True
        )
        self.history_action.setShortcut("Ctrl+H")
        self.history_action.setShortcutContext(Qt.ApplicationShortcut)
        self.history_action.setChecked(self.app_state.show_history)
        self.history_action.triggered.connect(self._toggle_history)
        settings_menu.addAction(self.history_action)
        
        self.constants_action = QAction(
            _get_icon("format-text-symbol"),
            "Constant Buttons (Coming Soon)",
            window,
            checkable=True
        )
        self.constants_action.setEnabled(False)
        self.constants_action.setChecked(self.app_state.show_constant_buttons)
        self.constants_action.triggered.connect(self._toggle_constants)
        settings_menu.addAction(self.constants_action)
        
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
        self.app_state.mode = mode
        self._update_mode_selection()
        if hasattr(self.window, 'update_layout'):
            self.window.update_layout()

    def _update_mode_selection(self) -> None:
        for mode, action in self._mode_actions.items():
            action.setChecked(mode == self.app_state.mode)

    def _toggle_history(self, checked: bool) -> None:
        self.app_state.show_history = checked
        if hasattr(self.window, 'update_layout'):
            self.window.update_layout()

    def _toggle_constants(self, checked: bool) -> None:
        self.app_state.show_constant_buttons = checked
