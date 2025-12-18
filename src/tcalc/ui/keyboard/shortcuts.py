from __future__ import annotations

from collections.abc import Callable

from tcalc.app_state import CalculatorMode
from tcalc.ui.controller.menubar import EditOperations, FileOperations, SettingsOperations

ShortcutId = Callable[..., object] | CalculatorMode


DEFAULT_ACTION_SHORTCUTS: dict[ShortcutId, str] = {
    FileOperations.quit: "Ctrl+Q",
    EditOperations.undo: "Ctrl+Z",
    EditOperations.redo: "Ctrl+Shift+Z",
    EditOperations.cut: "Ctrl+X",
    EditOperations.copy: "Ctrl+C",
    EditOperations.paste: "Ctrl+V",
    SettingsOperations.toggle_history: "Ctrl+H",
}
