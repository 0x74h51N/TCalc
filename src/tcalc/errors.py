import logging
from enum import Enum
from typing import NoReturn

_log = logging.getLogger("tcalc.errors")


class CalculatorError(Exception):
    """Exception raised for calculator operation errors."""

    pass


class ErrorKind(Enum):
    INVALID = "Invalid expression"
    MALFORMED = "Malformed Expression"
    MATH_ERR = "Math Error"


class Error(CalculatorError):
    pass


class Msg:
    """Single source for parser/controller user-facing message text."""

    # collection / point validation
    LIST_OF_LIST = "List of List not allowed"
    LIST_MIX = "List cannot mix scalars and points"
    EMPTY_POINT = "empty Point"
    POINT_ITEM_COLLECTION = "Point item cannot be a collection"
    BRACE_UNSUPPORTED = "brace collection type not supported"
    EMPTY_ELEMENT = "empty element"

    # rpn / internal
    POP_OPERAND = "Pop operand, not operand in stack."
    OPERAND_STACK_EMPTY = "Operand stack empty"

    # controller status hint
    USE_LIST_OR_POINT = "Use [ ] for lists or ( ) for points"

    @staticmethod
    def parse_number_error(detail: object) -> str:
        return f"Parse number token error: {detail}"

    @staticmethod
    def parse_expression_error(detail: object) -> str:
        return f"Parse expression token error: {detail}"

    @staticmethod
    def element_kind(kind: object) -> str:
        return f"element kind {kind}"

    @staticmethod
    def takes_one_argument(fn: str) -> str:
        return f"{fn} takes 1 argument"

    @staticmethod
    def not_for_list_or_point(fn: str) -> str:
        return f"{fn} is not defined for a list or point"


def raise_error(kind: ErrorKind, detail: object | None = None) -> NoReturn:
    message = kind.value
    if detail:
        _log.debug("%s: %s", message, detail)
        raise Error(f"{message}: {detail}")
    _log.debug("%s", message)
    raise Error(message)
