from __future__ import annotations

from enum import Enum


class Operation(Enum):
    # format: (value, symbol, precedence=None, associativity=None, arity=None, aliases=[])
    DIGIT = ("digit", "digit")

    # binary operators
    ADD = ("add", "+", 1, "left", "binary")
    SUB = ("sub", "-", 1, "left", "binary")
    MUL = ("mul", "x", 2, "left", "binary", ["*"])
    DIV = ("div", "÷", 2, "left", "binary", ["/"])
    POW = ("pow", "^", 3, "right", "binary")

    # postfix percent
    PERCENT = ("percent", "%", 4, "left", "postfix")

    DOT = ("dot", ".")
    OPEN_PAREN = ("open_paren", "(")
    CLOSE_PAREN = ("close_paren", ")")

    EQUALS = ("equals", "=")
    CLEAR = ("clear", "C")
    ALL_CLEAR = ("all_clear", "AC")
    BACKSPACE = ("backspace", "⌫")
    NEGATE = ("negate", "u-", 3, "right", "unary")
    SQRT = ("sqrt", "√", 4, "right", "unary", ["sqrt"])


    def __new__(cls, value, symbol, prec=None, assoc=None, arity=None, aliases=None):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.symbol = symbol
        obj.precedence = prec
        obj.associativity = assoc
        obj.arity = arity
        obj.aliases = aliases or []
        return obj


def get_symbols_with_aliases(filter_fn=None) -> set[str]:
    #Get all operation symbols including aliases, optionally filtered
    symbols = set()
    for op in Operation:
        if filter_fn and not filter_fn(op):
            continue
        if hasattr(op, 'symbol') and op.symbol:
            symbols.add(op.symbol)
            symbols.update(op.aliases)
    return symbols


def build_operator_table(filter_fn=None) -> dict[str, tuple[int, str]]:
    #Build operator precedence/associativity table including aliases
    table = {}
    for op in Operation:
        if filter_fn and not filter_fn(op):
            continue
        if hasattr(op, 'symbol') and op.symbol:
            if hasattr(op, 'precedence') and op.precedence is not None:
                table[op.symbol] = (op.precedence, op.associativity)
                for alias in op.aliases:
                    table[alias] = (op.precedence, op.associativity)
    return table


def build_operation_map(filter_fn=None) -> dict[str, Operation]:
    #Build operation lookup map including aliases
    op_map = {}
    for op in Operation:
        if filter_fn and not filter_fn(op):
            continue
        if hasattr(op, 'symbol') and op.symbol:
            op_map[op.symbol] = op
            for alias in op.aliases:
                op_map[alias] = op
    return op_map
