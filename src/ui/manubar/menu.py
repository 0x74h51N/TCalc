from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow


class Menubar:
    def __init__(self, window: QMainWindow) -> None:
        self.window = window
        self._create_menubar()

    def _create_menubar(self) -> None:
        menubar = self.window.menuBar()

        file_menu = menubar.addMenu("File")
        edit_menu = menubar.addMenu("Edit")
        settings_menu = menubar.addMenu("Settings")
        help_menu = menubar.addMenu("Help")

        exit_action = QAction("Exit", self.window)
        exit_action.triggered.connect(self.window.close)
        file_menu.addAction(exit_action)
