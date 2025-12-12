
from __future__ import annotations
import calc_native
from enum import Enum
from PySide6.QtCore import QSettings


class CalculatorMode(Enum):
    """Calculator operation modes."""
    SIMPLE = "simple"
    SCIENCE = "science"
    STATISTIC = "statistic"



AngleUnit = calc_native.AngleUnit


class AppState:
    """Global application state container (singleton) with persistent settings."""
    
    def __init__(self):
        self._settings = QSettings("TCalc", "TCalc")
        
        # Load from settings or use defaults
        mode_str = self._settings.value("mode", CalculatorMode.SIMPLE.value)
        self._mode = CalculatorMode(mode_str) if isinstance(mode_str, str) else CalculatorMode.SIMPLE
        
        self._show_history = self._settings.value("show_history", False, type=bool)
        
        self._show_constant_buttons = self._settings.value("show_constant_buttons", False, type=bool)
        
        # Undo/redo state (not persisted)
        self.history_index: int = -1
        self.redo_memory: str = ""
        
        # Angle unit for trig functions (not persisted)
        self.angle_unit = AngleUnit.DEG


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
