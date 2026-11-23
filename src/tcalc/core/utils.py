from collections.abc import Callable

import calc_native

type CalcValue = (
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


def fraction_text(value: calc_native.Rational) -> str:
    # One text for the result line's fraction view and MR, so the two cannot drift.
    if value.numerator < 0:
        return f"-\\frac{{{-value.numerator}}}{{{value.denominator}}}"
    return f"\\frac{{{value.numerator}}}{{{value.denominator}}}"


ELIDED = "..."


def collection_text(value: calc_native.Collection, item_text: Callable[[CalcValue], str]) -> str:
    """The brackets and the cap native's preview gives, each item written by item_text."""
    opener, closer, cap = value.preview()
    count = len(value)
    if cap is None:
        parts = [item_text(value[i]) for i in range(count)]
    else:
        head, tail = cap
        parts = [item_text(value[i]) for i in range(head)]
        parts.append(ELIDED)
        parts += [item_text(value[i]) for i in range(count - tail, count)]
    return opener + ", ".join(parts) + closer
