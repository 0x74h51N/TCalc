import math
from decimal import Decimal
from typing import TypeAlias

import calc_native

from .constants import I_UNIT_CHARS

_I64_MAX = (1 << 63) - 1
_I64_MIN = -(1 << 63)

CalcValue: TypeAlias = (
    int
    | float
    | complex
    | calc_native.BigReal
    | calc_native.BigComplex
    | calc_native.Rational
    | calc_native.Collection
)


def is_number_token(tok: calc_native.Token) -> bool:
    return tok.kind == calc_native.TokenKind.Number


def _parse_real_token(s: str) -> int | float | calc_native.BigReal:
    if "." not in s and "e" not in s.lower():
        return int(s)

    f = float(s)
    result: float | calc_native.BigReal = f

    if "e" in s.lower():
        float_ok = math.isfinite(f) and (f != 0.0 or Decimal(s) == 0)
        if not float_ok:
            try:
                result = calc_native.BigReal(s)
            except Exception:
                pass

    return result


def parse_number_token(
    s: str,
) -> CalcValue:
    if not s:
        return _parse_real_token(s)
    # normalize leading imag unit
    if s[0] in I_UNIT_CHARS:
        s = s[1:] + s[0]

    if s[-1] in I_UNIT_CHARS:
        real_part = s[:-1]
        real = 1 if real_part == "" else _parse_real_token(real_part)
        if isinstance(real, calc_native.BigReal):
            mag = float(str(real))
        else:
            mag = float(real)
        return complex(mag, 0.0) * 1j

    if "." not in s:
        try:
            v = int(s)
            if _I64_MIN <= v <= _I64_MAX:
                return v
            return _parse_real_token(s)
        except (ValueError, OverflowError):
            return _parse_real_token(s)

    # Decimal literal => Boost rational normalizes (GCD) internally.
    try:
        dec = Decimal(s)
        # |adjusted| > 18 is past i64's ~19 digits, so it can't be an i64 Rational;
        # bail before as_integer_ratio() materializes a giant int
        if abs(dec.adjusted()) > 18:
            return _parse_real_token(s)
        num, den = dec.as_integer_ratio()
        if num < _I64_MIN or num > _I64_MAX or den > _I64_MAX:
            return _parse_real_token(s)
        return calc_native.Rational(num, den)
    except Exception:
        return _parse_real_token(s)


def is_int_like(v: float, eps: float = 1e-12) -> bool:
    return math.isfinite(v) and abs(v - round(v)) <= eps
