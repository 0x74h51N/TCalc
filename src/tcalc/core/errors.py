import logging
from enum import Enum

from tcalc.core.engine import CalculatorError


class ErrorKind(Enum):
    INVALID = "Invalid expression"
    MALFORMED = "Malformed Expression"
    MATH_ERR = "Math Error"


class Error(CalculatorError):
    pass


def raise_error(kind: ErrorKind, detail: object | None = None) -> None:
    message = kind.value
    if detail:
        logging.error("%s: %s", message, detail)
    else:
        logging.error("%s", message)
    raise Error(message)
