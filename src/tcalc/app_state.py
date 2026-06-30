#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import calc_native
from PySide6.QtCore import QSettings

from tcalc.core.utils import CalcValue


class KeypadPreset(Enum):
    """Keypad layout presets (which keypads/docks are shown)."""

    SIMPLE = "simple"
    SCIENCE = "science"
    STATISTIC = "statistic"


class DockKind(Enum):
    """Toggleable dock widgets in the main window."""

    HISTORY = "history"
    NUMPAD = "numpad"
    FUNCPAD = "funcpad"
    TRIGPAD = "trigpad"


@dataclass(frozen=True)
class PresetLayout:
    visible_keypads: tuple[DockKind, ...]
    angle_visible: bool


PRESET_LAYOUTS: dict[KeypadPreset, PresetLayout] = {
    KeypadPreset.SIMPLE: PresetLayout((DockKind.NUMPAD,), angle_visible=False),
    KeypadPreset.SCIENCE: PresetLayout(
        (DockKind.TRIGPAD, DockKind.NUMPAD, DockKind.FUNCPAD), angle_visible=True
    ),
}


class RenderMode(Enum):
    """Display expression render modes."""

    MATH = "math"
    FLAT = "flat"
    RAW = "raw"


AngleUnit = calc_native.AngleUnit


class AppState:
    """Global application state container (singleton) with persistent settings."""

    _DOCK_SETTINGS_KEYS: dict[DockKind, str] = {
        DockKind.HISTORY: "show_history",
        DockKind.NUMPAD: "show_numpad",
        DockKind.FUNCPAD: "show_funcpad",
        DockKind.TRIGPAD: "show_trigpad",
    }

    def __init__(self):
        self._settings = QSettings("TCalc", "TCalc")

        stored_preset = self._settings.value("keypad_preset", KeypadPreset.SIMPLE.value)
        try:
            self._keypad_preset: KeypadPreset = KeypadPreset(stored_preset)
        except ValueError:
            self._keypad_preset = KeypadPreset.SIMPLE

        stored_custom = self._settings.value("active_custom_id", None)
        self._active_custom_id: int | None = (
            int(str(stored_custom)) if stored_custom not in (None, "") else None
        )

        self._history_mode: RenderMode = RenderMode(
            self._settings.value("history_mode", RenderMode.FLAT.value)
        )

        self._dock_states: dict[DockKind, bool] = {
            kind: bool(self._settings.value(key, False, type=bool))
            for kind, key in self._DOCK_SETTINGS_KEYS.items()
        }

        self._show_constant_buttons: bool = bool(
            self._settings.value("show_constant_buttons", False, type=bool)
        )

        self._angle_visible: bool = bool(self._settings.value("angle_visible", False, type=bool))
        # Undo/redo state (not persisted)
        self.history_index: int = -1
        self.redo_cached_exprs: str = ""

        # Angle unit for trig functions (not persisted)
        self.angle_unit = AngleUnit.DEG

        # Hyperbolic toggle (not persisted)
        self.hyp = False

        # Memory slot (not persisted)
        self.memory: CalcValue | None = None

        # Shifted (not persisted)
        self.shifted = False

    @property
    def keypad_preset(self) -> KeypadPreset:
        return self._keypad_preset

    @keypad_preset.setter
    def keypad_preset(self, value: KeypadPreset) -> None:
        self._keypad_preset = value
        self._settings.setValue("keypad_preset", value.value)

    @property
    def angle_visible(self) -> bool:
        return self._angle_visible

    @angle_visible.setter
    def angle_visible(self, value: bool) -> None:
        self._angle_visible = value
        self._settings.setValue("angle_visible", value)

    @property
    def active_custom_id(self) -> int | None:
        return self._active_custom_id

    @active_custom_id.setter
    def active_custom_id(self, value: int | None) -> None:
        self._active_custom_id = value
        if value is None:
            self._settings.remove("active_custom_id")
        else:
            self._settings.setValue("active_custom_id", value)

    @property
    def history_mode(self) -> RenderMode:
        return self._history_mode

    @history_mode.setter
    def history_mode(self, value: RenderMode) -> None:
        self._history_mode = value
        self._settings.setValue("history_mode", value.value)

    @property
    def show_constant_buttons(self) -> bool:
        return self._show_constant_buttons

    @show_constant_buttons.setter
    def show_constant_buttons(self, value: bool) -> None:
        self._show_constant_buttons = value
        self._settings.setValue("show_constant_buttons", value)

    def set_show_constant_buttons(self, value: bool) -> None:
        self.show_constant_buttons = value

    def is_dock_open(self, kind: DockKind) -> bool:
        return self._dock_states[kind]

    def set_dock_open(self, kind: DockKind, value: bool) -> None:
        self._dock_states[kind] = value
        self._settings.setValue(self._DOCK_SETTINGS_KEYS[kind], value)


# Global singleton instance
_app_state: AppState | None = None


def get_app_state() -> AppState:
    """Get the global application state instance."""
    global _app_state
    if _app_state is None:
        _app_state = AppState()
    return _app_state
