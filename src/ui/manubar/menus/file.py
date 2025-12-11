from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar,QMainWindow

class FileMenu:
    def __init__ (self, menu:QMenuBar, window: QMainWindow):
        file_menu = menu.addMenu("File")

        exit_action = QAction("Exit", window)
        exit_action.triggered.connect(window.close)
        file_menu.addAction(exit_action)