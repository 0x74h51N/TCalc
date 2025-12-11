from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar,QMainWindow

class FileMenu:
    def __init__ (self, menu:QMenuBar, window: QMainWindow):
        file_menu = menu.addMenu("File")
        
        def get_icon(theme_name: str) -> QIcon:
            icon = QIcon.fromTheme(theme_name)
            return icon if not icon.isNull() else QIcon()

        exit_action = QAction(
            get_icon("application-exit"),
            "Exit",
            window
        )
        exit_action.triggered.connect(window.close)
        file_menu.addAction(exit_action)