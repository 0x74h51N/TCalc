from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar, QMainWindow

from ...controller.edit_operations import EditOperations


class EditMenu:
    def __init__(self, menu: QMenuBar, window: QMainWindow):
        self.window = window
        self.edit_ops = EditOperations(window)
        
        edit_menu = menu.addMenu("Edit")
        
        def get_icon(theme_name: str) -> QIcon:
            icon = QIcon.fromTheme(theme_name)
            return icon if not icon.isNull() else QIcon()
        
        # Undo
        undo_action = QAction(
            get_icon("edit-undo"),
            "Undo",
            window
        )
        undo_action.setShortcut("Ctrl+Z")
        undo_action.setShortcutContext(Qt.ApplicationShortcut)
        undo_action.triggered.connect(lambda: self.edit_ops.undo())
        edit_menu.addAction(undo_action)
        
        # Redo
        redo_action = QAction(
            get_icon("edit-redo"),
            "Redo",
            window
        )
        redo_action.setShortcut("Ctrl+Shift+Z")
        redo_action.setShortcutContext(Qt.ApplicationShortcut)
        redo_action.triggered.connect(lambda: self.edit_ops.redo())
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        # Cut
        cut_action = QAction(
            get_icon("edit-cut"),
            "Cut",
            window
        )
        cut_action.setShortcut("Ctrl+X")
        cut_action.setShortcutContext(Qt.ApplicationShortcut)
        cut_action.triggered.connect(lambda: self.edit_ops.cut())
        edit_menu.addAction(cut_action)

        # Copy
        copy_action = QAction(
            get_icon("edit-copy"),
            "Copy",
            window
        )
        copy_action.setShortcut("Ctrl+C")
        copy_action.setShortcutContext(Qt.ApplicationShortcut)
        copy_action.triggered.connect(lambda: self.edit_ops.copy())
        edit_menu.addAction(copy_action)
        
        # Paste
        paste_action = QAction(
            get_icon("edit-paste"),
            "Paste",
            window
        )
        paste_action.setShortcut("Ctrl+V")
        paste_action.setShortcutContext(Qt.ApplicationShortcut)
        paste_action.triggered.connect(lambda: self.edit_ops.paste())
        edit_menu.addAction(paste_action)
