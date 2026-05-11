#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from enum import Enum

import calc_native
from PySide6.QtCore import QSettings

from tcalc.core.utils import CalcValue


class CalculatorMode(Enum):
    """Calculator operation modes."""

    SIMPLE = "simple"
    SCIENCE = "science"
    STATISTIC = "statistic"


class DockKind(Enum):
    """Toggleable dock widgets in the main window."""

    HISTORY = "history"
    NUMPAD = "numpad"
    FUNCPAD = "funcpad"
    TRIGPAD = "trigpad"


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

        self._mode: CalculatorMode = CalculatorMode(
            self._settings.value("mode", CalculatorMode.SIMPLE.value)
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
    def mode(self) -> CalculatorMode:
        return self._mode

    @mode.setter
    def mode(self, value: CalculatorMode) -> None:
        self._mode = value
        self._settings.setValue("mode", value.value)

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
