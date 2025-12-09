from __future__ import annotations


from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QFrame

from ..core import Calculator
from .manubar.menu import Menubar
from .controller.controller import CalculatorController
from .keypad.keypad import Keypad
from .display.display import Display


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.calculator: Calculator = Calculator()

        self.setWindowTitle("TCalc")
        self.resize(360, 520)
        self.setMinimumSize(280, 370)

        central = QWidget(self)
        self.setCentralWidget(central)

        m_layout = QVBoxLayout(central)
        m_layout.setContentsMargins(0, 0, 0, 0)
        m_layout.setSpacing(0)

        self.menubar = Menubar(self)


        #Display
        self.display = Display(parent=central)

        m_layout.addWidget(self.display, 3)

        #Controller binding
        self.controller = CalculatorController(self.calculator, self.display)

        #horiz line
        line = QFrame(self)
        line.setFrameShape(QFrame.HLine) 
        line.setFrameShadow(QFrame.Sunken)
        line.setLineWidth(1)

        m_layout.addWidget(line) 

        #Keypad
        self.keypad = Keypad(on_key_pressed=self.controller.handle_key, parent=central)
        m_layout.addWidget(self.keypad, 7)



        
