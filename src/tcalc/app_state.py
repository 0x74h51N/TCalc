from __future__ import annotations

from enum import Enum
from typing import TypeAlias

import calc_native
from PySide6.QtCore import QSettings


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


CalcValue: TypeAlias = int | float | complex | calc_native.BigReal | calc_native.BigComplex


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

        self._show_keypad: bool = bool(self._settings.value("show_keypad", False, type=bool))

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

    @property
    def history_mode(self) -> RenderMode:
        return self._history_mode

    @history_mode.setter
    def history_mode(self, value: RenderMode) -> None:
        self._history_mode = value
        self._settings.setValue("history_mode", value.value)

    @property
    def show_keypad(self) -> bool:
        return self._show_keypad

    @show_keypad.setter
    def show_keypad(self, value: bool) -> None:
        self._show_keypad = value
        self._settings.setValue("show_keypad", value)

    @property
    def show_constant_buttons(self) -> bool:
        return self._show_constant_buttons

    @show_constant_buttons.setter
    def show_constant_buttons(self, value: bool) -> None:
        self._show_constant_buttons = value
        self._settings.setValue("show_constant_buttons", value)


# Global singleton instance
_app_state: AppState | None = None


def get_app_state() -> AppState:
    """Get the global application state instance."""
    global _app_state
    if _app_state is None:
        _app_state = AppState()
    return _app_state
