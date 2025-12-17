from __future__ import annotations

import json
from pathlib import Path
from typing import List

from PySide6.QtCore import QStandardPaths
from tcalc.app_state import CalculatorMode

MAX_HISTORY_ITEMS = 100


def _get_data_dir() -> Path:
    """Get platform-specific app data directory."""
    path = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    data_dir = Path(path)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def load_history(mode: CalculatorMode) -> List[str]:
    """Load history from JSON file."""
    history_file = _get_data_dir()/f"history_{mode.value}.json"
    
    if not history_file.exists():
        return []
    
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("history", [])
    except (json.JSONDecodeError, IOError):
        return []


def save_history(history: List[str], mode: CalculatorMode) -> None:
    """Save history to JSON file."""
    history_file = _get_data_dir()/f"history_{mode.value}.json"
    
    # Limit history size
    if len(history) > MAX_HISTORY_ITEMS:
        history = history[-MAX_HISTORY_ITEMS:]
    
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump({"history": history}, f, ensure_ascii=False, indent=2)
    except IOError:
        print("History storage write error: ", IOError)
        pass


def clear_history_file(mode: CalculatorMode) -> None:
    """Clear history file."""
    history_file = _get_data_dir()/f"history_{mode.value}.json"
    
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump({"history": []}, f)
    except IOError:
        pass
