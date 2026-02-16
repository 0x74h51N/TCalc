from __future__ import annotations

from typing import Dict

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction

from .keymap import DEFAULT_ACTION_SHORTCUTS, ShortcutId


class ShortcutManager:
    def __init__(self) -> None:
        self._settings = QSettings("TCalc", "TCalc")
        self._bindings: Dict[ShortcutId, QAction] = {}

    def _settings_key(self, action_id: ShortcutId) -> str | None:
        """Get settings key for action, None if lambda or invalid."""
        qualname = action_id.__qualname__
        if "." not in qualname:
            return None
        owner, name = qualname.split(".", 1)
        return f"{owner.removesuffix('Operations').lower()}.{name}"

    def bind_action(
        self,
        action_id: ShortcutId,
        action: QAction,
        context: Qt.ShortcutContext = Qt.ShortcutContext.ApplicationShortcut,
    ) -> None:
        self._bindings[action_id] = action
        action.setShortcutContext(context)
        shortcut = self.get_shortcut(action_id)
        if shortcut:
            action.setShortcut(shortcut)

    def get_shortcut(self, action_id: ShortcutId) -> str:
        key = self._settings_key(action_id)
        value: object = self._settings.value(f"shortcuts/{key}", "", type=str)
        if not isinstance(value, str):
            value = str(value)
        return value or DEFAULT_ACTION_SHORTCUTS.get(action_id, "")

    def refresh(self) -> None:
        for action_id, action in self._bindings.items():
            action.setShortcut(self.get_shortcut(action_id))
