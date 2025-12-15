from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QTimer
from PySide6.QtWidgets import QLineEdit

from .shortcuts import get_operation_for_key

if TYPE_CHECKING:
    from ..controller import CalculatorController
    from ..widgets.calc.keypad.keypad import Keypad


class KeyboardHandler:
    
    def __init__(self, expression_input: QLineEdit, keypad: Keypad, controller: CalculatorController):
        self._expression_input = expression_input
        self._keypad = keypad
        self._controller = controller
    
    def handle_key_press(self, event: QEvent) -> bool:

        # If expression input has focus, let it handle the input
        if self._expression_input.hasFocus():
            return False
        
        
        result = get_operation_for_key(event.key())
        if result:
            label, operation = result
            button = self._keypad.get_button(label)
            if button:
                # Button pressed like tricks
                button.setProperty("pressed", True)
                button.style().unpolish(button)
                button.style().polish(button)
                button.click()
                # Remove pressed property after delay
                def reset():
                    button.setProperty("pressed", False)
                    button.style().unpolish(button)
                    button.style().polish(button)
                QTimer.singleShot(100, reset)
            elif operation in self._controller._handlers:
                self._controller.handle_key(label, operation)
            return True
        
        return False
