from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import calc_native
from PySide6.QtCore import QStandardPaths

from tcalc.app_state import CalculatorMode
from tcalc.ui.config import history_config

_log = logging.getLogger("tcalc.ui.history.storage")


@dataclass(slots=True)
class HistoryEntry:
    expression: str
    result: str
    tokens: list[calc_native.Token] = field(default_factory=list)


def _get_data_dir() -> Path:
    """Get platform-specific app data directory."""
    path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    data_dir = Path(path)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _history_path(mode: CalculatorMode) -> Path:
    return _get_data_dir() / f"history_{mode.value}.dat"


def load_history(mode: CalculatorMode) -> List[HistoryEntry]:
    """Load history from binary file."""
    path = _history_path(mode)

    if not path.exists():
        return []

    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        _log.debug("Failed to load history file: %s", path, exc_info=True)
        return []


def save_history(history: List[HistoryEntry], mode: CalculatorMode) -> None:
    """Save history to binary file."""
    path = _history_path(mode)

    max_items = int(history_config["max_items"])
    if len(history) > max_items:
        history = history[-max_items:]

    try:
        with open(path, "wb") as f:
            pickle.dump(history, f, protocol=pickle.HIGHEST_PROTOCOL)
    except IOError:
        _log.debug("History storage write error: %s", path, exc_info=True)


def clear_history_file(mode: CalculatorMode) -> None:
    """Clear history file."""
    path = _history_path(mode)

    try:
        with open(path, "wb") as f:
            pickle.dump([], f, protocol=pickle.HIGHEST_PROTOCOL)
    except IOError:
        _log.debug("Failed to clear history file: %s", path, exc_info=True)
