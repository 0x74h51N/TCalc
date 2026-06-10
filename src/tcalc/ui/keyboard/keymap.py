from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

from tcalc.core.ops import Operation
from tcalc.ui.controller.menubar import EditOperations, FileOperations, SettingsOperations
from tcalc.ui.widgets.calc.display.expression.expression import Expression

_KEY_TO_OPERATION: list[tuple[int, Operation]] = [
    # Operators
    (int(Qt.Key.Key_Plus), Operation.ADD),
    (int(Qt.Key.Key_Minus), Operation.SUB),
    (int(Qt.Key.Key_Asterisk), Operation.MUL),
    (int(Qt.Key.Key_Slash), Operation.DIV),
    (int(Qt.Key.Key_Percent), Operation.PERCENT),
    (int(Qt.Key.Key_AsciiCircum), Operation.POW),
    # Parentheses
    (int(Qt.Key.Key_ParenLeft), Operation.OPEN_PAREN),
    (int(Qt.Key.Key_ParenRight), Operation.CLOSE_PAREN),
    # Actions
    (int(Qt.Key.Key_Return), Operation.EQUALS),
    (int(Qt.Key.Key_Enter), Operation.EQUALS),
    (int(Qt.Key.Key_Equal), Operation.EQUALS),
    (int(Qt.Key.Key_Backspace), Operation.BACKSPACE),
    (int(Qt.Key.Key_Delete), Operation.CLEAR),
]

_SPECIAL_LABEL_KEYS: dict[int, tuple[str, Operation]] = {
    int(Qt.Key.Key_Period): (".", Operation.DOT),
    int(Qt.Key.Key_Comma): (",", Operation.COMMA),
}

EXPRESSION_KEY_MAP = {
    int(Qt.Key.Key_Left): Expression.navigate_left,
    int(Qt.Key.Key_Right): Expression.navigate_right,
    int(Qt.Key.Key_Up): Expression.navigate_up,
    int(Qt.Key.Key_Down): Expression.navigate_down,
}

OVERRIDE_SHORTCUTS = (
    QKeySequence.StandardKey.Undo,
    QKeySequence.StandardKey.Redo,
    QKeySequence.StandardKey.Cut,
    QKeySequence.StandardKey.Copy,
)

ShortcutId = Callable[..., object]
DEFAULT_ACTION_SHORTCUTS: dict[ShortcutId, str] = {
    FileOperations.quit: "Ctrl+Q",
    EditOperations.undo: "Ctrl+Z",
    EditOperations.redo: "Ctrl+Shift+Z",
    EditOperations.cut: "Ctrl+X",
    EditOperations.copy: "Ctrl+C",
    EditOperations.paste: "Ctrl+V",
    SettingsOperations.toggle_history: "Ctrl+H",
    SettingsOperations.toggle_numpad: "Ctrl+N",
    SettingsOperations.toggle_funcpad: "Ctrl+F",
    SettingsOperations.toggle_trigpad: "Ctrl+T",
    SettingsOperations.restore_default_layout: "CTRL+.",
}


def _build_key_map() -> dict[int, tuple[str, Operation]]:
    key_map: dict[int, tuple[str, Operation]] = {}

    for i in range(10):
        key_map[int(getattr(Qt.Key, f"Key_{i}"))] = (str(i), Operation.DIGIT)

    for qt_key, op in _KEY_TO_OPERATION:
        key_map[qt_key] = (op.symbol, op)

    key_map.update(_SPECIAL_LABEL_KEYS)

    return key_map


KEY_MAP: dict[int, tuple[str, Operation]] = _build_key_map()


def get_operation_for_key(key: int) -> tuple[str, Operation] | None:
    return KEY_MAP.get(key)


def get_expression_action_for_key(key: int):
    return EXPRESSION_KEY_MAP.get(key)
