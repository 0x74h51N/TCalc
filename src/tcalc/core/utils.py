import math

import calc_native

def is_number_token(tok: object) -> bool:
    return tok.kind == calc_native.TokenKind.Number
  


def _parse_real_token(s: str) -> int | float | calc_native.BigReal:
    if "." not in s and "e" not in s.lower():
        return int(s)
    if ("e" in s.lower()) and hasattr(calc_native, "BigReal"):
        try:
            return calc_native.BigReal(s)
        except Exception:
            return float(s)
    return float(s)


def parse_number_token(s: str) -> int | float | complex | calc_native.BigReal:
    if not s:
        return _parse_real_token(s)

    # normalize leading 'i' to trailing 'i'
    if s[0] in {"i", "I"}:
        s = s[1:] + "i"

    if s[-1] in {"i", "I"}:
        real_part = s[:-1]
        real = 1 if real_part == "" else _parse_real_token(real_part)
        if isinstance(real, getattr(calc_native, "BigReal", ())):
            mag = float(str(real))
        else:
            mag = float(real)
        return complex(mag, 0.0) * 1j

    return _parse_real_token(s)


def is_int_like(v: float, eps: float = 1e-12) -> bool:
    return math.isfinite(v) and abs(v - round(v)) <= eps
