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
