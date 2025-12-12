from __future__ import annotations

import json
from pathlib import Path
from typing import List

from PySide6.QtCore import QStandardPaths


MAX_HISTORY_ITEMS = 100


def _get_data_dir() -> Path:
    """Get platform-specific app data directory."""
    path = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    data_dir = Path(path)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _get_history_file() -> Path:
    """Get history file path."""
    return _get_data_dir() / "history.json"


def load_history() -> List[str]:
    """Load history from JSON file."""
    history_file = _get_history_file()
    
    if not history_file.exists():
        return []
    
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("history", [])
    except (json.JSONDecodeError, IOError):
        return []


def save_history(history: List[str]) -> None:
    """Save history to JSON file."""
    history_file = _get_history_file()
    
    # Limit history size
    if len(history) > MAX_HISTORY_ITEMS:
        history = history[-MAX_HISTORY_ITEMS:]
    
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump({"history": history}, f, ensure_ascii=False, indent=2)
    except IOError:
        pass  # Silently fail if can't write


def clear_history_file() -> None:
    """Clear history file."""
    history_file = _get_history_file()
    
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump({"history": []}, f)
    except IOError:
        pass
