from __future__ import annotations

from PySide6.QtCore import Qt

from ...core import Operation


_KEY_TO_OPERATION: list[tuple[int, Operation]] = [
    # Operators
    (Qt.Key_Plus, Operation.ADD),
    (Qt.Key_Minus, Operation.SUB),
    (Qt.Key_Asterisk, Operation.MUL),
    (Qt.Key_Slash, Operation.DIV),
    (Qt.Key_Percent, Operation.PERCENT),
    (Qt.Key_AsciiCircum, Operation.POW),

    # Parentheses
    (Qt.Key_ParenLeft, Operation.OPEN_PAREN),
    (Qt.Key_ParenRight, Operation.CLOSE_PAREN),

    # Actions
    (Qt.Key_Return, Operation.EQUALS),
    (Qt.Key_Enter, Operation.EQUALS),
    (Qt.Key_Equal, Operation.EQUALS),
    (Qt.Key_Backspace, Operation.BACKSPACE),
    (Qt.Key_Delete, Operation.CLEAR),
]

_SPECIAL_LABEL_KEYS: dict[int, tuple[str, Operation]] = {
    Qt.Key_Period: (".", Operation.DOT),
    Qt.Key_Comma: (".", Operation.DOT),
}


def _build_key_map() -> dict[int, tuple[str, Operation]]:
    key_map: dict[int, tuple[str, Operation]] = {}

    for i in range(10):
        key_map[getattr(Qt, f"Key_{i}")] = (str(i), Operation.DIGIT)

    for qt_key, op in _KEY_TO_OPERATION:
        key_map[qt_key] = (op.symbol, op)

    key_map.update(_SPECIAL_LABEL_KEYS)

    return key_map


KEY_MAP: dict[int, tuple[str, Operation]] = _build_key_map()


def get_operation_for_key(key: int) -> tuple[str, Operation] | None:
    return KEY_MAP.get(key)

