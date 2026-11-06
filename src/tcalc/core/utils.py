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
