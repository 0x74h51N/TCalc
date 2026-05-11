from __future__ import annotations

from tcalc.app_state import CalculatorMode, DockKind, get_app_state


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
        self._window.sync_dock(DockKind.HISTORY, checked)

    def toggle_constants(self, checked: bool) -> None:
        self._app_state.show_constant_buttons = checked
        self._window.update_layout()

    def toggle_numpad(self, checked: bool) -> None:
        self._window.sync_dock(DockKind.NUMPAD, checked)

    def toggle_funcpad(self, checked: bool) -> None:
        self._window.sync_dock(DockKind.FUNCPAD, checked)

    def toggle_trigpad(self, checked: bool) -> None:
        self._window.sync_dock(DockKind.TRIGPAD, checked)

    def add_custom_pad(self) -> None:
        self._window.add_custom_pad()

    def restore_default_layout(self) -> None:
        self._window.apply_def_dock_layout()
