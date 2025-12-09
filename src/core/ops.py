from __future__ import annotations

from enum import Enum


class Operation(Enum):
    # format: (value, symbol, precedence=None, associativity=None, arity=None)
    DIGIT = ("digit", "digit")

    # binary operators
    ADD = ("add", "+", 1, "left", "binary")
    SUB = ("sub", "-", 1, "left", "binary")
    MUL = ("mul", "x", 2, "left", "binary")
    DIV = ("div", "÷", 2, "left", "binary")
    # postfix percent
    PERCENT = ("percent", "%", 4, "left", "postfix")

    DOT = ("dot", ".")
    OPEN_PAREN = ("open_paren", "(")
    CLOSE_PAREN = ("close_paren", ")")

    EQUALS = ("equals", "=")
    CLEAR = ("clear", "C")
    ALL_CLEAR = ("all_clear", "AC")
    NEGATE = ("negate", "u-", 3, "right", "unary")

    def __new__(cls, value: str, symbol: str | None = None, precedence: int | None = None, associativity: str | None = None, arity: str | None = None):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.symbol = symbol
        obj.precedence = precedence
        obj.associativity = associativity
        obj.arity = arity
        return obj
