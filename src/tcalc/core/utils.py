import math
from typing import TypeAlias

import calc_native

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


def is_int_like(v: float, eps: float = 1e-12) -> bool:
    return math.isfinite(v) and abs(v - round(v)) <= eps
