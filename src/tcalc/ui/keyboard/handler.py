from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QLineEdit

from .keymap import get_operation_for_key

if TYPE_CHECKING:
    from tcalc.ui.controller import CalculatorController
    from tcalc.ui.widgets.calc.keypad.keypad import Keypad


class _ShortcutOverrideFilter(QObject):
    def __init__(self, target: QLineEdit):
        super().__init__(target)
        self._target = target

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._target and event.type() == QEvent.Type.ShortcutOverride:
            if isinstance(event, QKeyEvent) and (
                event.matches(QKeySequence.StandardKey.Undo)
                or event.matches(QKeySequence.StandardKey.Redo)
                or event.matches(QKeySequence.StandardKey.Cut)
                or event.matches(QKeySequence.StandardKey.Copy)
            ):
                event.ignore()
                return True
        return False


class KeyboardHandler:
    def __init__(
        self, expression_input: QLineEdit, keypad: Keypad, controller: CalculatorController
    ):
        self._expression_input = expression_input
        self._keypad = keypad
        self._controller = controller
        self._shortcut_override_filter = _ShortcutOverrideFilter(self._expression_input)
        self._expression_input.installEventFilter(self._shortcut_override_filter)

    def handle_key_press(self, event: QKeyEvent) -> bool:
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
