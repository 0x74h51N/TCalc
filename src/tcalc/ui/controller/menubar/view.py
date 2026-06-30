from __future__ import annotations

from PySide6.QtWidgets import QInputDialog

from tcalc.app_state import DockKind, KeypadPreset, get_app_state
from tcalc.ui.layout_presets import LayoutPreset


class ViewOperations:
    def __init__(self, window) -> None:
        self._window = window
        self._app_state = get_app_state()

    def set_preset(self, preset: KeypadPreset) -> None:
        self._app_state.active_custom_id = None
        self._app_state.keypad_preset = preset
        self._app_state.history_index = -1
        self._window.apply_preset_layout(preset)

    def toggle_history(self, checked: bool) -> None:
        self._window.sync_dock(DockKind.HISTORY, checked)

    def toggle_constants(self, checked: bool) -> None:
        self._app_state.show_constant_buttons = checked
        self._window.update_layout()

    def toggle_angle(self, checked: bool) -> None:
        self._app_state.angle_visible = checked
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
        self._window.restore_default_layout()

    def save_custom_preset(self, name: str) -> LayoutPreset:
        state, angle = self._window.capture_layout()
        rec = self._window._layout_presets.add(name, state, angle)
        self._app_state.active_custom_id = rec.id
        self._window._save_window_state()  # pair window/state with the new active preset
        return rec

    def add_custom_preset(self) -> None:
        name, ok = QInputDialog.getText(self._window, "Save Layout Preset", "Name:")
        if ok and name.strip():
            self.save_custom_preset(name.strip())

    def apply_custom_preset(self, preset_id: int) -> None:
        rec = self._window._layout_presets.get(preset_id)
        if rec is None:
            return
        self._app_state.active_custom_id = preset_id
        self._app_state.history_index = -1
        self._window.apply_custom_layout(rec)

    def rename_custom_preset(self, preset_id: int, name: str) -> None:
        self._window._layout_presets.rename(preset_id, name)

    def update_custom_preset(self, preset_id: int) -> None:
        state, angle = self._window.capture_layout()
        self._window._layout_presets.update(preset_id, state, angle)

    def delete_custom_preset(self, preset_id: int) -> None:
        self._window._layout_presets.delete(preset_id)
        if self._app_state.active_custom_id == preset_id:
            self._app_state.active_custom_id = None
            self._window.apply_preset_layout(self._app_state.keypad_preset)
