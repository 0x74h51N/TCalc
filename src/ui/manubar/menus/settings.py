from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar, QMainWindow

from ....app_state import get_app_state, CalculatorMode


class SettingsMenu:

    def __init__(self, menu: QMenuBar, window: QMainWindow):
        self.app_state = get_app_state()
        self.window = window
        
        settings_menu = menu.addMenu("Settings")
        
        # Modes
        self.simple_action = QAction("Simple Mode", window, checkable=True)
        self.science_action = QAction("Science Mode", window, checkable=True)
        self.statistic_action = QAction("Statistic Mode", window, checkable=True)
        
        self._update_mode_selection()
        
        self.simple_action.triggered.connect(
            lambda: self._set_mode(CalculatorMode.SIMPLE)
        )
        self.science_action.triggered.connect(
            lambda: self._set_mode(CalculatorMode.SCIENCE)
        )
        self.statistic_action.triggered.connect(
            lambda: self._set_mode(CalculatorMode.STATISTIC)
        )
        
        settings_menu.addAction(self.simple_action)
        settings_menu.addAction(self.science_action)
        settings_menu.addAction(self.statistic_action)
        
        settings_menu.addSeparator()
        
        # Visibility toggles
        self.history_action = QAction("Show History", window, checkable=True)
        self.history_action.setChecked(self.app_state.show_history)
        self.history_action.triggered.connect(self._toggle_history)
        settings_menu.addAction(self.history_action)
        
        self.constants_action = QAction("Constant Buttons", window, checkable=True)
        self.constants_action.setChecked(self.app_state.show_constant_buttons)
        self.constants_action.triggered.connect(self._toggle_constants)
        settings_menu.addAction(self.constants_action)
        
        settings_menu.addSeparator()
        
        # Configuration actions
        keyboard_action = QAction("Configure Keyboard Shortcuts", window)

        settings_menu.addAction(keyboard_action)
        #TODO: Keyboard shortcuts dialog


        config_action = QAction("Configure TCalc", window)

        settings_menu.addAction(config_action)
        #TODO: TCalc config dialog


    def _set_mode(self, mode: CalculatorMode) -> None:
        self.app_state.mode = mode
        self._update_mode_selection()

    def _update_mode_selection(self) -> None:
        current_mode = self.app_state.mode
        self.simple_action.setChecked(current_mode == CalculatorMode.SIMPLE)
        self.science_action.setChecked(current_mode == CalculatorMode.SCIENCE)
        self.statistic_action.setChecked(current_mode == CalculatorMode.STATISTIC)

    def _toggle_history(self, checked: bool) -> None:
        self.app_state.show_history = checked
        if hasattr(self.window, 'update_layout'):
            self.window.update_layout()

    def _toggle_constants(self, checked: bool) -> None:
        self.app_state.show_constant_buttons = checked
