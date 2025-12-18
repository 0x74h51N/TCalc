from __future__ import annotations

from PySide6.QtCore import Qt

from ...core import Operation

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
    int(Qt.Key.Key_Comma): (".", Operation.DOT),
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
