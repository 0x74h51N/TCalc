from __future__ import annotations


from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QFrame
from PySide6.QtCore import QSize

from ..core import Calculator
from .manubar.menu import Menubar
from .controller.controller import CalculatorController
from .controller.edit_operations import EditOperations
from .widgets import CalcWidget, History
from .config import window, get_history_width_from_total
from src.app_state import get_app_state

class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        app_state = get_app_state()

        self.calculator: Calculator = Calculator()
        self.setWindowTitle("TCalc")

        central = QWidget(self)
        self.setCentralWidget(central)

        m_layout = QHBoxLayout(central)
        m_layout.setContentsMargins(0, 0, 0, 0)
        m_layout.setSpacing(0)

        # Calc widget (display + keypad)
        self.calc_widget = CalcWidget(
            on_key_pressed=lambda label, op: None, 
            parent=central
        )
        self.calc_widget.setMinimumSize(
            window["calc_min_width"],
            window["min_height"]
        )
        m_layout.addWidget(self.calc_widget, window["calc_stretch"])

        line = QFrame(self)
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setLineWidth(1)

        self.menubar = Menubar(self)
        
        # Connect settings menu to visibility changes
        settings_menu = self.menubar.settings_menu
        settings_menu.window = self  # Pass window reference for UI updates

        self.divider = QFrame(self)
        self.divider.setFrameShape(QFrame.VLine)
        self.divider.setFrameShadow(QFrame.Sunken)
        self.divider.setLineWidth(1)
        self.divider.setVisible(app_state.show_history)

        self.history = History(parent=central)
        self.history.setMinimumSize(
            window["history_min_width"],
            window["min_height"]
        )
        self.history.setVisible(app_state.show_history)

        # Add to layout
        m_layout.addWidget(self.divider)
        m_layout.addWidget(self.history, window["history_stretch"])
        
        # Adjust window to content size
        self.adjustSize()
        self._update_history_size()
       
        # Edit operations
        self.edit_ops = EditOperations(self)

        # Controller binding
        self.controller = CalculatorController(self.calculator, self.calc_widget.display, self.history, self.edit_ops)
        
        # Connect keypad to controller
        self.calc_widget.keypad._on_key_pressed = self.controller.handle_key

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_history_size()

    def _update_history_size(self):
        central = self.centralWidget()
        if central:
            width = central.width()
            history_width = get_history_width_from_total(width)
            self.history.setMinimumWidth(history_width)

    def update_layout(self) -> None:
        app_state = get_app_state()
        self.history.setVisible(app_state.show_history)
        self.divider.setVisible(app_state.show_history)
        
        # Adjust minimum width based on visibility
        if app_state.show_history:
            min_width = window["calc_min_width"] + window["history_min_width"]
        else:
            min_width = window["calc_min_width"]
        
        self.setMinimumWidth(min_width)
        self.adjustSize()
        self.resize(self.minimumSizeHint())

    def sizeHint(self) -> QSize:
        central = self.centralWidget()
        if central:
            size = central.sizeHint()
        else:
            size = QSize(600, 300)
        
        # Add menubar height if exists
        if self.menuBar():
            size.setHeight(size.height() + self.menuBar().height())
        
        return size

        
