#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QLineEdit

from .keymap import OVERRIDE_SHORTCUTS, get_expression_action_for_key, get_operation_for_key

if TYPE_CHECKING:
    from tcalc.ui.controller import CalculatorController
    from tcalc.ui.widgets.calc.display.expression import Expression
    from tcalc.ui.widgets.keypad.keypad import Keypad


class KeyboardHandler(QObject):
    def __init__(self, editor: Expression, keypad: Keypad, controller: CalculatorController):
        super().__init__(editor)
        self._editor = editor
        self._keypad = keypad
        self._controller = controller

        for le in self._editor.expression_inputs():
            le.installEventFilter(self)

        self._editor.input_created.connect(self._on_input_created)

    def _on_input_created(self, le: QLineEdit):
        le.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if isinstance(event, QKeyEvent):
            if event.type() == QEvent.Type.ShortcutOverride:
                return self._handle_shortcut_override(event)
            if event.type() == QEvent.Type.KeyPress:
                return self.handle_key_press(event)
        return False

    def _handle_shortcut_override(self, event: QKeyEvent) -> bool:
        for sk in OVERRIDE_SHORTCUTS:
            if event.matches(sk):
                event.ignore()
                return True
        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        expr_action = get_expression_action_for_key(event.key())

        if expr_action:
            bound = expr_action.__get__(self._editor, type(self._editor))
            return bound()

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
