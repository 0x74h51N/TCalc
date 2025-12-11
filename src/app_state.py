from __future__ import annotations

from enum import Enum


class CalculatorMode(Enum):
    #Calculator modes
    SIMPLE = "simple"
    SCIENCE = "science"
    STATISTIC = "statistic"


class AppState:
    #Global state container
    def __init__(self):
        self.mode: CalculatorMode = CalculatorMode.SIMPLE
        self.show_history: bool = False
        self.show_constant_buttons: bool = False
        
        # Undo/redo state
        self.history_index: int = -1  # Current position in history (-1 = not navigating)
        self.redo_memory: str = ""    # Stores expression when navigating history


# Global singleton instance
_app_state: AppState | None = None


def get_app_state() -> AppState:
    #Get the global states instance
    global _app_state
    if _app_state is None:
        _app_state = AppState()
    return _app_state
