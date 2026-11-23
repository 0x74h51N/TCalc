#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""The expected value of a probe row from python-flint, and the error of the row's value against it."""

from __future__ import annotations

import math
import struct
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from fractions import Fraction

import calc_native
from flint import acb, arb, ctx, fmpq, fmpz

from probes.rows import UNIT_COLUMN, Layer, OperandKind, ProbeError, Row, angle_unit
from tcalc.core.constants import CONST_BY_ID, I_UNIT_CHARS
from tcalc.core.ops import OP_BY_ID

REF_DIGITS = 80
RESIDUAL_DIGITS = 3
NOT_GRADED = "not graded"
NO_SINGLE_DOUBLE = "no single double"
NOT_FINITE = "not finite"
EXACT = "exact"
DECIMAL_BASE = 10
PERCENT = 100
MAGNITUDE_BITS = (1 << 63) - 1  # a double's bits without the sign
HISTOGRAM_TOP = 9  # the last bucket holds every count from here up

OpId = calc_native.OpId
TokenKind = calc_native.TokenKind

# acb(), lower() and upper() round to the working precision, so every public step runs at REF_DIGITS
at_ref_digits = ctx.workdps(REF_DIGITS)


# Exact while the ops keep it exact, as TCalc's Rational arm does; a ball once they do not.
type Ref = fmpq | acb
type Meaning = Callable[[Sequence[Ref]], Ref | None]
# a collection operand, spread into the args of the op it feeds, as mean[1,2,3] does
type Item = Ref | tuple[Ref, ...] | None
type Meanings = Mapping[calc_native.OpId, Meaning]


def _ball(value: Ref) -> acb:
    return acb(value) if isinstance(value, fmpq) else value


def _fmpq(exact: Fraction) -> fmpq:
    return fmpq(exact.numerator, exact.denominator)


def _fraction(text: str) -> fmpq:
    """A decimal or p/q text, read exactly."""
    return _fmpq(Fraction(text))


def _finite_decimal(text: str) -> fmpq | None:
    """A BigReal's text, which can be inf or nan; those have no exact value to grade against."""
    value = Decimal(text)
    return _fmpq(Fraction(value)) if value.is_finite() else None


def _finite_double(text: str) -> fmpq | None:
    value = float.fromhex(text)
    return _fmpq(Fraction(value)) if math.isfinite(value) else None


def _number(text: str) -> Ref:
    """A number token: 2i is an imaginary literal."""
    if text[-1] in I_UNIT_CHARS:
        return acb(0, _fraction(text[:-1]))
    return _fraction(text)


def _is_negative_real(value: Ref) -> bool:
    if isinstance(value, fmpq):
        return value < 0
    return value.imag.is_zero() and value.real < 0


def _exact_values(args: Sequence[Ref]) -> list[fmpq] | None:
    exact = [arg for arg in args if isinstance(arg, fmpq)]
    return exact if len(exact) == len(args) else None


def _exact_whole(args: Sequence[Ref]) -> list[int] | None:
    exact = _exact_values(args)
    whole = [int(arg.p) for arg in exact or [] if arg.q == 1]
    return whole if len(whole) == len(args) else None


def _arithmetic(exact: Callable[[fmpq, fmpq], fmpq], ball: Callable[[acb, acb], acb]) -> Meaning:
    """An op that stays exact on two fractions, as + - · ÷ do."""

    def meaning(args: Sequence[Ref]) -> Ref:
        pair = _exact_values(args)
        return exact(*pair) if pair is not None else ball(_ball(args[0]), _ball(args[1]))

    return meaning


_divide = _arithmetic(lambda a, b: a / b, lambda a, b: a / b)


def _analytic(function: Callable[[acb], acb]) -> Meaning:
    """An op that is a ball whatever its operand, as exp or sin is."""
    return lambda args: function(_ball(args[0]))


def _integer_root(value: fmpz, degree: int) -> fmpz | None:
    """The degree-th root of a non-negative integer when it is a whole number."""
    root = value.root(degree)
    return root if root**degree == value else None


def _exact_root(value: fmpq, degree: int) -> fmpq | None:
    """The real degree-th root of a fraction when it is a fraction, as TCalc's exact rows keep 8⌄3."""
    if value < 0 and degree % 2 == 0:
        return None
    numerator = _integer_root(abs(value.p), degree)
    denominator = _integer_root(value.q, degree)
    if numerator is None or denominator is None:
        return None
    root = fmpq(numerator, denominator)
    return -root if value < 0 else root


def _c99_side(function: Callable[[acb], acb]) -> Meaning:
    """asin, acos and atanh on their cut above 1: TCalc and C99 take the side above, python-flint the side below."""

    def meaning(args: Sequence[Ref]) -> Ref:
        value = _ball(args[0])
        result = function(value)
        # f(conj z) = conj f(z), so the conjugate is the value above the cut; an arb comparison is true only when certain
        on_cut_above_one = value.imag.is_zero() and value.real > 1
        return result.conjugate() if on_cut_above_one else result

    return meaning


def _pow_values(base: Ref, exponent: Ref) -> Ref:
    # TCalc's real first rule (docs/glossary.md): an exact p/q with odd q on a negative base is real
    if isinstance(exponent, fmpq) and isinstance(base, fmpq):
        root = _exact_root(base, int(exponent.q))
        if root is not None:
            return root ** int(exponent.p)
    if isinstance(exponent, fmpq) and int(exponent.q) % 2 == 1 and _is_negative_real(base):
        magnitude = (-_ball(base)) ** _ball(exponent)
        return -magnitude if int(exponent.p) % 2 == 1 else magnitude
    return _ball(base) ** _ball(exponent)


def _pow(args: Sequence[Ref]) -> Ref:
    return _pow_values(args[0], args[1])


def _root(args: Sequence[Ref]) -> Ref:
    radicand, degree = args
    inverse = 1 / degree if isinstance(degree, fmpq) else 1 / _ball(degree)
    return _pow_values(radicand, inverse)


def _power_of(exponent: int) -> Meaning:
    return lambda args: _pow_values(args[0], fmpq(exponent))


def _on_integers(function: Callable[[list[int]], int]) -> Meaning:
    """An op defined on whole numbers only, as gcd or nCr is; anything else is not graded."""

    def meaning(args: Sequence[Ref]) -> Ref | None:
        whole = _exact_whole(args)
        return fmpq(function(whole)) if whole is not None else None

    return meaning


def _fact(args: Sequence[Ref]) -> Ref:
    whole = _exact_whole(args)
    if whole is not None:
        return fmpq(math.factorial(whole[0]))
    return (_ball(args[0]) + 1).gamma()


# toward zero, as the kernels' trunc_div and static_cast do, never floor
def _trunc(value: fmpq) -> fmpq:
    # fmpq.trunc exists at runtime but not in python-flint's stub
    return fmpq(value.floor() if value >= 0 else value.ceil())


def _trunc_quotient(a: fmpq, b: fmpq) -> fmpq:
    return _trunc(a / b)


def _trunc_ball_quotient(a: acb, b: acb) -> acb:
    quotient = (a / b).real
    return acb(quotient.floor() if quotient >= 0 else quotient.ceil())


def _rounded(function: Callable[[fmpq], fmpq]) -> Meaning:
    """floor, ceil and trunc: graded on an exact operand only."""

    def meaning(args: Sequence[Ref]) -> Ref | None:
        value = args[0]
        return function(value) if isinstance(value, fmpq) else None

    return meaning


def _total(args: Sequence[Ref]) -> Ref:
    exact = _exact_values(args)
    return sum(exact, fmpq(0)) if exact is not None else sum((_ball(arg) for arg in args), acb(0))


def _mean(args: Sequence[Ref]) -> Ref:
    total = _total(args)
    return total / len(args)


def _variance(args: Sequence[Ref], ddof: int) -> Ref:
    mean = _ball(_mean(args))
    squares = sum(((_ball(arg) - mean) ** 2 for arg in args), acb(0))
    return squares / (len(args) - ddof)


def _ordered(pick: Callable[[list[fmpq]], fmpq]) -> Meaning:
    """min, max and median: graded on exact operands, which order."""

    def meaning(args: Sequence[Ref]) -> Ref | None:
        exact = _exact_values(args)
        return pick(exact) if exact is not None else None

    return meaning


def _median(values: list[fmpq]) -> fmpq:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def _power_of_ten(value: fmpz) -> int | None:
    exponent = len(str(value)) - 1
    return exponent if fmpz(DECIMAL_BASE) ** exponent == value else None


def _exact_log10(value: fmpq) -> fmpq | None:
    """log of a power of ten is exact in TCalc: log(1000) is 3, log(0.01) is -2."""
    if value <= 0:
        return None
    numerator, denominator = _power_of_ten(value.p), _power_of_ten(value.q)
    if numerator is None or denominator is None:
        return None
    return fmpq(numerator - denominator)


def _log10(args: Sequence[Ref]) -> Ref:
    value = args[0]
    exact = _exact_log10(value) if isinstance(value, fmpq) else None
    return exact if exact is not None else _ball(value).log() / acb(DECIMAL_BASE).log()


OP_MEANINGS: dict[calc_native.OpId, Meaning] = {
    OpId.Add: _arithmetic(lambda a, b: a + b, lambda a, b: a + b),
    OpId.Sub: _arithmetic(lambda a, b: a - b, lambda a, b: a - b),
    OpId.Mul: _arithmetic(lambda a, b: a * b, lambda a, b: a * b),
    OpId.Div: _divide,
    OpId.Mod: _arithmetic(
        lambda a, b: a - b * _trunc_quotient(a, b), lambda a, b: a - b * _trunc_ball_quotient(a, b)
    ),
    OpId.IntDiv: _arithmetic(_trunc_quotient, _trunc_ball_quotient),
    OpId.Pow: _pow,
    OpId.Root: _root,
    OpId.Sqrt: lambda args: _root([args[0], fmpq(2)]),
    OpId.Cbrt: lambda args: _root([args[0], fmpq(3)]),
    OpId.Sqr: _power_of(2),
    OpId.Cube: _power_of(3),
    OpId.Recip: _power_of(-1),
    OpId.Negate: lambda args: -args[0],
    OpId.UnaryPlus: lambda args: args[0],
    OpId.Percent: lambda args: _divide([args[0], fmpq(PERCENT)]),
    OpId.Exp: _analytic(acb.exp),
    OpId.Ln: _analytic(acb.log),
    OpId.Log: _log10,
    OpId.Pow10: lambda args: _pow_values(fmpq(DECIMAL_BASE), args[0]),
    OpId.Sin: _analytic(acb.sin),
    OpId.Cos: _analytic(acb.cos),
    OpId.Tan: _analytic(acb.tan),
    OpId.Sinh: _analytic(acb.sinh),
    OpId.Cosh: _analytic(acb.cosh),
    OpId.Tanh: _analytic(acb.tanh),
    OpId.Asin: _c99_side(acb.asin),
    OpId.Acos: _c99_side(acb.acos),
    OpId.Atan: _analytic(acb.atan),
    OpId.Asinh: _analytic(acb.asinh),
    OpId.Acosh: _analytic(acb.acosh),
    OpId.Atanh: _c99_side(acb.atanh),
    OpId.Polar: _analytic(lambda angle: (acb(0, 1) * angle).exp()),
    OpId.Gamma: _analytic(acb.gamma),
    OpId.Fact: _fact,
    OpId.Choose: _on_integers(lambda whole: math.comb(whole[0], whole[1])),
    OpId.Permute: _on_integers(lambda whole: math.perm(whole[0], whole[1])),
    OpId.Gcd: _on_integers(lambda whole: math.gcd(*whole)),
    OpId.Lcm: _on_integers(lambda whole: math.lcm(*whole)),
    OpId.Floor: _rounded(lambda value: fmpq(value.floor())),
    OpId.Ceil: _rounded(lambda value: fmpq(value.ceil())),
    OpId.Trunc: _rounded(_trunc),
    OpId.Sum: _total,
    OpId.Mean: _mean,
    OpId.Min: _ordered(min),
    OpId.Max: _ordered(max),
    OpId.Median: _ordered(_median),
    OpId.Var: lambda args: _variance(args, 1),
    OpId.VarP: lambda args: _variance(args, 0),
    OpId.Std: lambda args: _ball(_variance(args, 1)).sqrt(),
    OpId.StdP: lambda args: _ball(_variance(args, 0)).sqrt(),
}

# the half turn in each unit TCalc reads angles in; radians need no conversion
_HALF_TURN = {calc_native.AngleUnit.DEG: 180, calc_native.AngleUnit.GRAD: 200}
# in half turns, so an exact angle stays exact: cos(90) in degrees is cos_pi(1/2), exactly 0
_HALF_TURN_MEANINGS: dict[calc_native.OpId, Callable[[acb], acb]] = {
    OpId.Sin: acb.sin_pi,
    OpId.Cos: acb.cos_pi,
    OpId.Tan: acb.tan_pi,
    OpId.Polar: acb.exp_pi_i,
}
_ANGLE_OUT = (OpId.Asin, OpId.Acos, OpId.Atan)


def _angle_in(function: Callable[[acb], acb], half_turn: int) -> Meaning:
    """sin, cos, tan and polar read their operand in the unit, a fraction of a half turn."""
    return lambda args: function(_ball(args[0] / half_turn))


def _angle_out(meaning: Meaning, radians_per_unit: acb) -> Meaning:
    """asin, acos and atan give an angle: the radians are turned into the unit."""

    def converted(args: Sequence[Ref]) -> Ref | None:
        result = meaning(args)
        return _ball(result) / radians_per_unit if result is not None else None

    return converted


@at_ref_digits
def _meanings_in(half_turn: int) -> dict[calc_native.OpId, Meaning]:
    radians_per_unit = acb(arb.pi()) / half_turn
    return {
        **OP_MEANINGS,
        **{op: _angle_in(function, half_turn) for op, function in _HALF_TURN_MEANINGS.items()},
        **{op: _angle_out(OP_MEANINGS[op], radians_per_unit) for op in _ANGLE_OUT},
    }


MEANINGS: dict[calc_native.AngleUnit, Meanings] = {
    calc_native.AngleUnit.RAD: OP_MEANINGS,
    **{unit: _meanings_in(half_turn) for unit, half_turn in _HALF_TURN.items()},
}


_NAMED_CONSTANTS: dict[calc_native.ConstId, Callable[[], Ref]] = {
    calc_native.ConstId.Pi: lambda: acb(arb.pi()),
    calc_native.ConstId.EulerNumber: lambda: acb(arb.const_e()),
    calc_native.ConstId.GoldenRatio: lambda: (1 + acb(5).sqrt()) / 2,
    calc_native.ConstId.Tau: lambda: 2 * acb(arb.pi()),
    calc_native.ConstId.Imaginary: lambda: acb(0, 1),
}


def _constant(const_id: calc_native.ConstId) -> Ref:
    named = _NAMED_CONSTANTS.get(const_id)
    if named is not None:
        return named()
    # a measured constant is defined by the decimal its table entry holds; the stub types it Any
    value = CONST_BY_ID[const_id].value
    assert isinstance(value, float)
    return _fraction(repr(value))


_OP_BY_NAME = {name: spec.id for spec in OP_BY_ID.values() for name in (spec.symbol, *spec.aliases)}


def _arity(op: calc_native.OpId) -> int:
    return 2 if OP_BY_ID[op].arity == calc_native.OpArity.Binary else 1


def _tokens_of(part: calc_native.Token | list[calc_native.Token]) -> list[calc_native.Token]:
    return part if isinstance(part, list) else [part]


def _apply(meanings: Meanings, op: calc_native.OpId, items: Sequence[Item]) -> Ref | None:
    meaning = meanings.get(op)
    (first, *rest) = items
    args = first if isinstance(first, tuple) and not rest else items
    known = [arg for arg in args if isinstance(arg, fmpq | acb)]
    return meaning(known) if meaning is not None and len(known) == len(args) else None


def _paren(meanings: Meanings, token: calc_native.Token) -> Item:
    values = [
        _value_of_tokens(meanings, _tokens_of(element)) for element in token.as_paren().elements
    ]
    known = [value for value in values if isinstance(value, fmpq | acb)]
    if len(known) < len(values):
        return None
    return known[0] if len(known) == 1 else tuple(known)


def _call(meanings: Meanings, token: calc_native.Token) -> Item:
    call = token.as_call()
    args = [_value_of_tokens(meanings, _tokens_of(arg)) for arg in call.args]
    return _apply(meanings, call.op_id, args)


def _latex_op(meanings: Meanings, token: calc_native.Token) -> Item:
    latex = token.as_latex()
    sides = [_value_of_tokens(meanings, latex.left), _value_of_tokens(meanings, latex.right)]
    return _apply(meanings, latex.op_id, sides)


# Subscript, Sum and Prod have no meaning here yet, so a row that holds one is not graded
_LATEX: dict[calc_native.LatexKind, Callable[[Meanings, calc_native.Token], Item]] = {
    calc_native.LatexKind.Frac: _latex_op,
    calc_native.LatexKind.Pow: _latex_op,
    calc_native.LatexKind.Root: _latex_op,
}


def _latex(meanings: Meanings, token: calc_native.Token) -> Item:
    walk = _LATEX.get(token.as_latex().kind)
    return walk(meanings, token) if walk is not None else None


_OPERANDS: dict[calc_native.TokenKind, Callable[[Meanings, calc_native.Token], Item]] = {
    TokenKind.Number: lambda _, token: _number(token.as_number().value),
    TokenKind.Const: lambda _, token: _constant(token.as_const().id),
    TokenKind.Paren: _paren,
    TokenKind.Call: _call,
    TokenKind.Latex: _latex,
}


def _value_of_tokens(meanings: Meanings, tokens: Sequence[calc_native.Token]) -> Item:
    """TCalc's own RPN walked with the meanings of one angle unit; None as soon as a part has no meaning."""
    stack: list[Item] = []
    for token in calc_native.shunting_yard(list(tokens)):
        if token.kind == TokenKind.Op:
            op = token.as_op().op_id
            args = stack[-_arity(op) :]
            del stack[-_arity(op) :]
            stack.append(_apply(meanings, op, args))
        else:
            operand = _OPERANDS.get(token.kind)
            stack.append(operand(meanings, token) if operand is not None else None)
    return stack[0] if len(stack) == 1 else None


@at_ref_digits
def expected_of_expression(text: str, unit: calc_native.AngleUnit) -> Ref | None:
    """The mathematical value of the text: 0.1 is one tenth."""
    value = _value_of_tokens(MEANINGS[unit], calc_native.tokenize_string(text).tokens)
    # a collection result has no single value to grade
    return value if isinstance(value, fmpq | acb) else None


def _complex_hex(text: str) -> Ref | None:
    real, imag = (_finite_double(part) for part in text.split(","))
    return acb(real, imag) if real is not None and imag is not None else None


_OPERAND_READERS: dict[OperandKind, Callable[[str], Ref | None]] = {
    OperandKind.INT: _fraction,
    OperandKind.DBL: _finite_double,
    OperandKind.RAT: _fraction,
    OperandKind.BIG: _finite_decimal,
    OperandKind.CX: _complex_hex,
}


def _operand(word: str) -> Ref | None:
    prefix, _, exact = word.partition(":")
    reader = _OPERAND_READERS.get(OperandKind(prefix))
    return reader(exact) if reader is not None else None


@at_ref_digits
def expected_of_operands(
    op: calc_native.OpId, operands: Sequence[str], unit: calc_native.AngleUnit
) -> Ref | None:
    """The exact result on the operands as they are held: dbl:0x1.999999999999ap-4 is that double."""
    return _apply(MEANINGS[unit], op, [_operand(word) for word in operands])


def _operand_row(text: str) -> tuple[calc_native.OpId, list[str]] | None:
    """An input written as an op and typed operands, or None for an expression."""
    op_word, *operands = text.split()
    op = _OP_BY_NAME.get(op_word)
    if (
        op is None
        or not operands
        or any(word.partition(":")[0] not in OperandKind for word in operands)
    ):
        return None
    return op, operands


@at_ref_digits
def double_of(value: acb) -> float | complex | None:
    """The double each part's ball rounds to at both ends, or None when the ends disagree."""
    real, imag = _double_of_part(value.real), _double_of_part(value.imag)
    if real is None or imag is None:
        return None
    return real if value.imag.is_zero() else complex(real, imag)


def _double_of_part(part: arb) -> float | None:
    low, high = float(part.lower()), float(part.upper())
    return low if low == high else None


def _place(value: float) -> int:
    """The double's place among all doubles, so two places differ by the doubles between them."""
    bits = int.from_bytes(struct.pack("<d", value), "little", signed=True)
    return bits if bits >= 0 else -(bits & MAGNITUDE_BITS)


def ulps(got: float, want: float) -> int | None:
    """How many doubles apart got is from want; None when an inf or nan leaves no distance."""
    if got == want:
        return 0
    if not (math.isfinite(got) and math.isfinite(want)):
        return None
    return abs(_place(got) - _place(want))


def _reference_text(reference: Ref) -> str:
    return _ball(reference).real.str(REF_DIGITS, radius=False)


@at_ref_digits
def bigreal_residual(value: calc_native.BigReal, reference: Ref) -> tuple[str, str]:
    """value minus the reference through TCalc's own Sub, and that residual relative to it."""
    exact = _ball(reference)
    exact_big = calc_native.BigReal(_reference_text(reference))
    residual = calc_native.apply(
        calc_native.Calculator(), OpId.Sub, [value, exact_big], calc_native.AngleUnit.RAD
    )
    if not isinstance(residual, calc_native.BigReal):
        raise ProbeError(f"BigReal minus BigReal gave a {type(residual).__name__}")
    residual_text = calc_native.decimal_text(residual, 0)
    relative = acb(_fraction(residual_text)) / exact if not exact.is_zero() else acb(0)
    return residual_text, relative.real.str(RESIDUAL_DIGITS, radius=False)


@dataclass(frozen=True)
class Grade:
    expected: str
    error: str
    ulps: int | None


_UNGRADED = Grade("", NOT_GRADED, None)


def _expected_text(reference: Ref) -> str:
    if isinstance(reference, fmpq):
        return str(reference)
    double = double_of(reference)
    return repr(double) if double is not None else reference.str(RESIDUAL_DIGITS)


def _double_grade(got: complex, reference: Ref) -> Grade:
    want = double_of(_ball(reference))
    if want is None:
        return Grade(_expected_text(reference), NO_SINGLE_DOUBLE, None)
    want_complex = complex(want)
    parts = [(got.real, want_complex.real)]
    if want_complex.imag or got.imag:
        parts.append((got.imag, want_complex.imag))
    counts = [ulps(got_part, want_part) for got_part, want_part in parts]
    measured = [count for count in counts if count is not None]
    if len(measured) < len(counts):
        return Grade(repr(want), NOT_FINITE, None)
    return Grade(repr(want), ", ".join(f"{count} ulp" for count in measured), max(measured))


def _exact_grade(got: fmpq, reference: Ref) -> Grade:
    if isinstance(reference, fmpq):
        error = EXACT if got == reference else f"off by {got - reference}"
        return Grade(str(reference), error, None)
    if reference.contains(acb(got)):
        return Grade(_expected_text(reference), EXACT, None)
    return Grade(
        _expected_text(reference), f"off by {(acb(got) - reference).str(RESIDUAL_DIGITS)}", None
    )


def _bigreal_grade(text: str, reference: Ref) -> Grade:
    residual, relative = bigreal_residual(calc_native.BigReal(text), reference)
    return Grade(_reference_text(reference), f"residual {residual} rel {relative}", None)


# keyed by the row's type column, which rows.type_name writes from the class
_GRADERS: dict[str, Callable[[str, Ref], Grade]] = {
    cls.__name__: grader
    for cls, grader in (
        (float, lambda text, reference: _double_grade(complex(float(text)), reference)),
        (complex, lambda text, reference: _double_grade(complex(text), reference)),
        (int, lambda text, reference: _exact_grade(_fraction(text), reference)),
        (calc_native.Rational, lambda text, reference: _exact_grade(_fraction(text), reference)),
        (calc_native.BigReal, _bigreal_grade),
    )
}


def _reference(text: str, unit: calc_native.AngleUnit) -> Ref | None:
    operand_row = _operand_row(text)
    if operand_row is None:
        return expected_of_expression(text, unit)
    op, operands = operand_row
    return expected_of_operands(op, operands, unit)


def _row_unit(row: Row) -> calc_native.AngleUnit:
    columns = dict(row.extra)
    if UNIT_COLUMN not in columns:
        raise ProbeError(f"the row {row.input!r} has no {UNIT_COLUMN} column to grade it in")
    return angle_unit(columns[UNIT_COLUMN])


@at_ref_digits
def grade_of(row: Row) -> Grade:
    """The row's value against the expected value its input names; an error row is not graded."""
    grader = _GRADERS.get(row.type)
    if grader is None:
        return _UNGRADED
    reference = _reference(row.input, _row_unit(row))
    return grader(row.value, reference) if reference is not None else _UNGRADED


# the layers that hold a value, which --ref grades and a test's claims sit beside
VALUE_LAYERS = (Layer.LITERAL, Layer.EVAL, Layer.BINDING, Layer.APPLY)


def finish(rows: Sequence[Row], beside: tuple[tuple[str, str], ...], ref: bool) -> list[Row]:
    """A test row's claims beside each value row, and the grade when --ref asks for it."""
    return [_finish_row(row, beside, ref) if row.layer in VALUE_LAYERS else row for row in rows]


def _finish_row(row: Row, beside: tuple[tuple[str, str], ...], ref: bool) -> Row:
    claimed = replace(row, extra=(*row.extra, *beside))
    return grade(claimed) if ref else claimed


def grade(row: Row) -> Row:
    result = grade_of(row)
    return replace(row, extra=(*row.extra, ("expected", result.expected), ("error", result.error)))


def _histogram(grades: Sequence[Grade]) -> str:
    counts = Counter(min(g.ulps, HISTOGRAM_TOP) for g in grades if g.ulps is not None)
    buckets = [f"{n}:{counts[n]}" for n in range(HISTOGRAM_TOP)]
    return " ".join([*buckets, f"{HISTOGRAM_TOP}+:{counts[HISTOGRAM_TOP]}"])


def _by_key(rows: Sequence[Row]) -> dict[tuple[str, Layer], Grade]:
    keys = Counter((row.input, row.layer) for row in rows)
    repeated = [key for key, count in keys.items() if count > 1]
    if repeated:
        raise ProbeError(f"a run holds the same input and layer twice: {repeated}")
    return {(row.input, row.layer): grade_of(row) for row in rows}


def compare(old: Sequence[Row], new: Sequence[Row]) -> str:
    """The ulp histogram of each run and how many rows got better or worse."""
    old_by_key = _by_key(old)
    new_by_key = _by_key(new)
    paired = [(old_by_key[key], new_by_key[key]) for key in old_by_key if key in new_by_key]
    measured = [(a.ulps, b.ulps) for a, b in paired if a.ulps is not None and b.ulps is not None]
    better = sum(1 for a, b in measured if b < a)
    worse = sum(1 for a, b in measured if b > a)
    unpaired = sorted(set(old_by_key) ^ set(new_by_key))
    lines = [
        f"old  {_histogram(list(old_by_key.values()))}",
        f"new  {_histogram(list(new_by_key.values()))}",
        f"better {better} worse {worse}",
        *(f"unpaired  {text}  {layer}" for text, layer in unpaired),
    ]
    return "\n".join(lines)
