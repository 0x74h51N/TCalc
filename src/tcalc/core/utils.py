import math
from decimal import Decimal

import calc_native

from .constants import I_UNIT_CHARS


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


def parse_number_token(s: str) -> int | float | complex | calc_native.BigReal:
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

    return _parse_real_token(s)


def is_int_like(v: float, eps: float = 1e-12) -> bool:
    return math.isfinite(v) and abs(v - round(v)) <= eps


def debug_tokens(tokens: list[calc_native.Token]):
    out = []
    for t in tokens:
        kind = t.kind.name
        if isinstance(t.data, calc_native.ParenToken):
            val = t.data.symbol
        elif isinstance(t.data, calc_native.NumberToken):
            val = t.data.value
        elif isinstance(t.data, calc_native.OpToken):
            val = t.symbol
        elif isinstance(t.data, calc_native.ExprToken):
            val = f"Expr({t.data.kind.name})"
        else:
            val = str(t)
        out.append(f"{kind}: {val}")
    print("DEBUG TOKENS ->", out)
