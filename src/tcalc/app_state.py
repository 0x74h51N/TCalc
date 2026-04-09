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


class RenderMode(Enum):
    """Display expression render modes."""

    MATH = "math"
    FLAT = "flat"
    RAW = "raw"


AngleUnit = calc_native.AngleUnit


class AppState:
    """Global application state container (singleton) with persistent settings."""

    def __init__(self):
        self._settings = QSettings("TCalc", "TCalc")

        self._mode: CalculatorMode = CalculatorMode(
            self._settings.value("mode", CalculatorMode.SIMPLE.value)
        )

        self._show_history: bool = bool(self._settings.value("show_history", False, type=bool))

        self._history_mode: RenderMode = RenderMode(
            self._settings.value("history_mode", RenderMode.FLAT.value)
        )

        self._show_numpad: bool = bool(self._settings.value("show_numpad", False, type=bool))
        self._show_funcpad: bool = bool(self._settings.value("show_funcpad", False, type=bool))
        self._show_trigpad: bool = bool(self._settings.value("show_trigpad", False, type=bool))

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
    def show_history(self) -> bool:
        return self._show_history

    @show_history.setter
    def show_history(self, value: bool) -> None:
        self._show_history = value
        self._settings.setValue("show_history", value)

    def set_show_history(self, value: bool) -> None:
        self.show_history = value

    @property
    def history_mode(self) -> RenderMode:
        return self._history_mode

    @history_mode.setter
    def history_mode(self, value: RenderMode) -> None:
        self._history_mode = value
        self._settings.setValue("history_mode", value.value)

    @property
    def show_numpad(self) -> bool:
        return self._show_numpad

    @show_numpad.setter
    def show_numpad(self, value: bool) -> None:
        self._show_numpad = value
        self._settings.setValue("show_numpad", value)

    def set_show_numpad(self, value: bool) -> None:
        self.show_numpad = value

    @property
    def show_funcpad(self) -> bool:
        return self._show_funcpad

    @show_funcpad.setter
    def show_funcpad(self, value: bool) -> None:
        self._show_funcpad = value
        self._settings.setValue("show_funcpad", value)

    def set_show_funcpad(self, value: bool) -> None:
        self.show_funcpad = value

    @property
    def show_trigpad(self) -> bool:
        return self._show_trigpad

    @show_trigpad.setter
    def show_trigpad(self, value: bool) -> None:
        self._show_trigpad = value
        self._settings.setValue("show_trigpad", value)

    def set_show_trigpad(self, value: bool) -> None:
        self.show_trigpad = value

    @property
    def show_constant_buttons(self) -> bool:
        return self._show_constant_buttons

    @show_constant_buttons.setter
    def show_constant_buttons(self, value: bool) -> None:
        self._show_constant_buttons = value
        self._settings.setValue("show_constant_buttons", value)

    def set_show_constant_buttons(self, value: bool) -> None:
        self.show_constant_buttons = value


# Global singleton instance
_app_state: AppState | None = None


def get_app_state() -> AppState:
    """Get the global application state instance."""
    global _app_state
    if _app_state is None:
        _app_state = AppState()
    return _app_state
