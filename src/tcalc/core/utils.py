import math
import re

_NUMBER_PATTERN = re.compile(r"(?:\d+\.\d*|\d+|\.\d+)(?:[eE][+-]?\d+)?")

try:
    import calc_native  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    calc_native = None

def is_number_token(tok: object) -> bool:
    if isinstance(tok, (int, float, complex)):
        return True
    if calc_native is not None and isinstance(tok, getattr(calc_native, "BigReal", ())):
        return True
    if isinstance(tok, str):
        return _NUMBER_PATTERN.fullmatch(tok) is not None
    return False

def parse_number_token(s: str) -> int | float | object:
    # int: "6"
    if "." not in s and "e" not in s.lower():
        return int(s)
    # scientific notation uses BigReal to avoid double overflow/underflow
    if ("e" in s.lower()) and calc_native is not None and hasattr(calc_native, "BigReal"):
        return calc_native.BigReal(s)
    # float: "6.0", ".5", "1e3" (fallback)
    return float(s)


def is_int_like(v: float, eps: float = 1e-12) -> bool:
    return math.isfinite(v) and abs(v - round(v)) <= eps
