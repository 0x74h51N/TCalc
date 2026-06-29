from __future__ import annotations

from tcalc.app_state import DockKind, KeypadPreset, get_app_state


class ViewOperations:
    def __init__(self, window) -> None:
        self._window = window
        self._app_state = get_app_state()

    def set_preset(self, preset: KeypadPreset) -> None:
        self._app_state.keypad_preset = preset
        self._app_state.history_index = -1
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
