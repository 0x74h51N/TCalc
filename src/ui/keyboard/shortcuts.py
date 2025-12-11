from __future__ import annotations

from PySide6.QtCore import Qt

from ...core import Operation


KEY_MAP: dict[int, tuple[str, Operation]] = {
    # Digits
    Qt.Key_0: ("0", Operation.DIGIT),
    Qt.Key_1: ("1", Operation.DIGIT),
    Qt.Key_2: ("2", Operation.DIGIT),
    Qt.Key_3: ("3", Operation.DIGIT),
    Qt.Key_4: ("4", Operation.DIGIT),
    Qt.Key_5: ("5", Operation.DIGIT),
    Qt.Key_6: ("6", Operation.DIGIT),
    Qt.Key_7: ("7", Operation.DIGIT),
    Qt.Key_8: ("8", Operation.DIGIT),
    Qt.Key_9: ("9", Operation.DIGIT),
    
    # Decimal
    Qt.Key_Period: (".", Operation.DOT),
    Qt.Key_Comma: (".", Operation.DOT),
    
    # Operators
    Qt.Key_Plus: (Operation.ADD.symbol, Operation.ADD),
    Qt.Key_Minus: (Operation.SUB.symbol, Operation.SUB),
    Qt.Key_Asterisk: (Operation.MUL.symbol, Operation.MUL),
    Qt.Key_Slash: (Operation.DIV.symbol, Operation.DIV),
    Qt.Key_Percent: (Operation.PERCENT.symbol, Operation.PERCENT),
    
    # Parentheses
    Qt.Key_ParenLeft: (Operation.OPEN_PAREN.symbol, Operation.OPEN_PAREN),
    Qt.Key_ParenRight: (Operation.CLOSE_PAREN.symbol, Operation.CLOSE_PAREN),
    
    # Actions
    Qt.Key_Return: (Operation.EQUALS.symbol, Operation.EQUALS),
    Qt.Key_Enter: (Operation.EQUALS.symbol, Operation.EQUALS),
    Qt.Key_Equal: (Operation.EQUALS.symbol, Operation.EQUALS),
    Qt.Key_Backspace: (Operation.BACKSPACE.symbol, Operation.BACKSPACE),
    Qt.Key_Delete: (Operation.CLEAR.symbol, Operation.CLEAR),
    Qt.Key_Escape: (Operation.ALL_CLEAR.symbol, Operation.ALL_CLEAR),
}


def get_operation_for_key(key: int) -> tuple[str, Operation] | None:
    return KEY_MAP.get(key)
