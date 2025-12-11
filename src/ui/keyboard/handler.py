from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from PySide6.QtCore import QEvent, QTimer
from PySide6.QtWidgets import QLineEdit

from .shortcuts import get_operation_for_key

if TYPE_CHECKING:
    from ...core import Operation
    from ..widgets.calc.keypad.keypad import Keypad


class KeyboardHandler:
    
    def __init__(self, expression_input: QLineEdit, keypad: "Keypad"):
        self._expression_input = expression_input
        self._keypad = keypad
    
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
            return True
        
        return False
