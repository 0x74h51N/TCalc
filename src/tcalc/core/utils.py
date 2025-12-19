import math
import re

import calc_native

_NUMBER_PATTERN = re.compile(r"(?:\d+\.\d*|\d+|\.\d+)(?:[eE][+-]?\d+)?")


def is_number_token(tok: object) -> bool:
    if isinstance(tok, (int, float, complex)):
        return True
    if isinstance(tok, getattr(calc_native, "BigReal", ())):
        return True
    if isinstance(tok, str):
        return _NUMBER_PATTERN.fullmatch(tok) is not None
    return False


def parse_number_token(s: str) -> int | float | calc_native.BigReal:
    # int: "6"
    if "." not in s and "e" not in s.lower():
        return int(s)
    # scientific notation uses BigReal to avoid double overflow/underflow
    if ("e" in s.lower()) and hasattr(calc_native, "BigReal"):
        try:
            return calc_native.BigReal(s)
        except Exception:
            # BigReal parsing can fail for extremely large exponents; fall back
            # to float so tokenization doesn't crash the UI.
            return float(s)
    # float: "6.0", ".5", "1e3" (fallback)
    return float(s)


def is_int_like(v: float, eps: float = 1e-12) -> bool:
    return math.isfinite(v) and abs(v - round(v)) <= eps
