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


def raise_error(kind: ErrorKind, detail: object | None = None) -> NoReturn:
    message = kind.value
    if detail:
        _log.debug("%s: %s", message, detail)
        raise Error(f"{message}: {detail}")
    _log.debug("%s", message)
    raise Error(message)
