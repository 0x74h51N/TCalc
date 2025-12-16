from __future__ import annotations


from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QFrame
from PySide6.QtCore import QSize

from ..core import Calculator
from .manubar.menu import Menubar
from .controller import CalculatorController, EditOperations
from .widgets import CalcWidget, History
from .config import window, get_history_width_from_total
from .keyboard import KeyboardHandler
from ..app_state import get_app_state, CalculatorMode
from .controller.utils import format_result

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
            parent=central
        )
        self.calc_widget.setMinimumSize(
            window["calc_min_width"],
            window["min_height"]
        )
        m_layout.addWidget(self.calc_widget, window["calc_stretch"])


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
       
        # Edit operations
        self.edit_ops = EditOperations(self)

        # Controller binding
        self.controller = CalculatorController(
            self.calculator, 
            self.calc_widget.display, 
            self.history, 
            self.edit_ops,
            self.calc_widget.topbar,
            )
        
        self.calc_widget.keypad.key_pressed.connect(self.controller.handle_key)
        self.calc_widget.topbar.key_pressed.connect(self.controller.handle_key)
        self.calc_widget.topbar.angle_changed.connect(self.controller.set_angle_unit)

        # Keyboard handler for global shortcuts
        self._keyboard_handler = KeyboardHandler(
            self.calc_widget.display.expression_label,
            self.calc_widget.keypad,
            self.controller
        )

        # Sync initial keypad state and size constraints
        self.update_layout()
        self._update_history_size()


    def keyPressEvent(self, event):
        if self._keyboard_handler.handle_key_press(event):
            return
        super().keyPressEvent(event)

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

        is_science = app_state.mode == CalculatorMode.SCIENCE
        keypad = self.calc_widget.keypad
        topbar = self.calc_widget.topbar
        keypad._science_widget.setVisible(is_science)
        topbar._angle_widget.setVisible(is_science)
        keypad._buttons["Shift"].setVisible(app_state.mode != CalculatorMode.SIMPLE)

        btn = topbar._angle_buttons.get(app_state.angle_unit)
        if btn:
            btn.setChecked(True)

        hyp_btn = keypad.get_button("Hyp")
        if hyp_btn:
            hyp_btn.setChecked(bool(app_state.hyp))

        keypad._buttons["Shift"].setChecked(bool(app_state.shifted))

        topbar.set_memory_available(app_state.memory is not None)
        self.history.set_memory("" if app_state.memory is None else format_result(app_state.memory))
        
        # Adjust minimum width based on visibility and mode
        calc_width = window["calc_min_width"]
        if app_state.mode == CalculatorMode.SCIENCE:
            calc_width += window.get("science_panel_width", 120)
        
        if app_state.show_history:
            min_width = calc_width + window["history_min_width"]
        else:
            min_width = calc_width
        
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

        
