from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar, QMainWindow

from tcalc.ui.controller.menubar import FileOperations
from ..defins import FILE_MENU_ACTIONS


def _get_icon(theme_name: str) -> QIcon:
    icon = QIcon.fromTheme(theme_name)
    return icon if not icon.isNull() else QIcon()


class FileMenu:
    def __init__(self, menu: QMenuBar, window: QMainWindow, shortcuts):
        self.ops = FileOperations(window)

        file_menu = menu.addMenu("File")

        for spec in FILE_MENU_ACTIONS:
            action = QAction(_get_icon(spec["icon"]), spec["text"], window, checkable=spec["checkable"])
            action.setEnabled(spec["enabled"])
            shortcuts.bind_action(spec["id"], action)
            action.triggered.connect(lambda checked=False, fn=spec["id"]: fn(self.ops))
            file_menu.addAction(action)
