from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction


from tcalc.app_state import CalculatorMode
from .shortcuts import DEFAULT_ACTION_SHORTCUTS, ShortcutId


class ShortcutManager:
    def __init__(self) -> None:
        self._settings = QSettings("TCalc", "TCalc")
        self._bindings: Dict[ShortcutId, QAction] = {}

    def _settings_key(self, action_id: ShortcutId) -> str:
        if isinstance(action_id, CalculatorMode):
            return f"mode.{action_id.value}"

        owner, name = action_id.__qualname__.split(".", 1)
        return f"{owner.removesuffix('Operations').lower()}.{name}"

    def bind_action(self, action_id: ShortcutId, action: QAction, context: Qt.ShortcutContext = Qt.ApplicationShortcut) -> None:
        self._bindings[action_id] = action
        action.setShortcutContext(context)
        action.setShortcut(self.get_shortcut(action_id))

    def get_shortcut(self, action_id: ShortcutId) -> str:
        key = self._settings_key(action_id)
        value = self._settings.value(f"shortcuts/{key}", "", type=str)
        return value or DEFAULT_ACTION_SHORTCUTS.get(action_id, "")

    def refresh(self) -> None:
        for action_id, action in self._bindings.items():
            action.setShortcut(self.get_shortcut(action_id))
