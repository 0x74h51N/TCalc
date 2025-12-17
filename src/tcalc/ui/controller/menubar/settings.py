from __future__ import annotations

from tcalc.app_state import CalculatorMode, get_app_state


class SettingsOperations:
    def __init__(self, window) -> None:
        self._window = window
        self._app_state = get_app_state()

    def set_mode(self, mode: CalculatorMode) -> None:
        self._app_state.mode = mode
        self._app_state.history_index = -1
        self._window.history.reload_from_storage(mode)
        self._window.update_layout()

    def toggle_history(self, checked: bool) -> None:
        self._app_state.show_history = checked
        self._window.update_layout()

    def toggle_constants(self, checked: bool) -> None:
        self._app_state.show_constant_buttons = checked
        self._window.update_layout()
