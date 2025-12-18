from __future__ import annotations

from typing import TYPE_CHECKING, Callable, cast

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar

from tcalc.ui.controller.menubar import FileOperations
from tcalc.ui.keyboard.shortcuts import ShortcutId

from ..defins import FILE_MENU_ACTIONS

if TYPE_CHECKING:
    from ...keyboard import ShortcutManager
    from ...window import MainWindow


def _get_icon(theme_name: str) -> QIcon:
    icon = QIcon.fromTheme(theme_name)
    return icon if not icon.isNull() else QIcon()


class FileMenu:
    def __init__(self, menu: QMenuBar, window: MainWindow, shortcuts: ShortcutManager):
        self.ops = FileOperations(window)

        file_menu = menu.addMenu("File")

        for spec in FILE_MENU_ACTIONS:
            icon = _get_icon(str(spec["icon"]))
            text = str(spec["text"])
            action = QAction(icon, text, window)
            action.setCheckable(bool(spec["checkable"]))
            action.setEnabled(bool(spec["enabled"]))

            action_id = cast(ShortcutId, spec["id"])
            shortcuts.bind_action(action_id, action)

            fn = cast(Callable[[FileOperations], None], spec["id"])
            action.triggered.connect(lambda checked=False, fn=fn: fn(self.ops))
            file_menu.addAction(action)
