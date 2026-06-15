#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from typing import Iterable, List, Sequence

import calc_native

from tcalc.errors import CalculatorError, ErrorKind, raise_error

from .constants import CONSTANTS
from .engine import Calculator
from .ops import OP_BY_ID
from .utils import CalcValue, is_number_token, parse_number_token


class ValueOperand:
    """A pre-evaluated runtime operand injected into an rpn stream, bypassing
    tokenize and collection construction. evaluate_rpn pushes `.value` straight
    onto the operand stack. Forward-compatible with variable resolution."""

    __slots__ = ("value",)

    def __init__(self, value: CalcValue) -> None:
        self.value = value


def tokenize_string(expression: str) -> List[calc_native.Token]:
    """Tokenize expression and return token list."""
    return calc_native.tokenize_string(expression).tokens


def tokenize(expression: str) -> calc_native.TokensBranch:
    """Tokenize expression and return full result with metadata."""
    return calc_native.tokenize_string(expression)


def shunting_yard(tokens: Sequence[calc_native.Token]) -> List[calc_native.Token]:
    return list(calc_native.shunting_yard(tokens))


def _pop_operand(operand_stack: List[CalcValue]) -> CalcValue:
    if not operand_stack:
        raise_error(ErrorKind.MALFORMED, "Pop operand, not operand in stack.")
    return operand_stack.pop()


def _coerce_token(tok: str | int | float) -> CalcValue:
    if isinstance(tok, str):
        if tok in CONSTANTS:
            return CONSTANTS[tok]
        try:
            return parse_number_token(tok)
        except Exception as e:
            raise_error(ErrorKind.INVALID, f"Parse number token error: {e}")
    if isinstance(tok, int):
        return calc_native.Rational(tok)
    return tok


def _eval_element(element, calculator: Calculator) -> CalcValue:
    """Element (arm 0 Token OR arm 1 list[Token]) -> CalcValue.

    Fast-paths arm 0 NumberToken (direct _coerce_token) and arm 0 ParenToken
    (direct _eval_paren_token recursion) to skip wrapping + shunting_yard +
    evaluate_rpn unnecessarily. Latex and multi-token arm 1 paths go through
    evaluate_rpn so TokenKind dispatch stays single-sourced there.
    """
    if isinstance(element, calc_native.Token):
        kind = element.kind
        if kind == calc_native.TokenKind.Number:
            return _coerce_token(element.data.value)
        if kind == calc_native.TokenKind.Paren:
            return _eval_paren_token(element.as_paren(), calculator)
        if kind == calc_native.TokenKind.Latex:
            return evaluate_rpn([element], calculator)
        raise_error(ErrorKind.INVALID, f"element kind {kind}")

    if not element:
        raise_error(ErrorKind.INVALID, "empty element")
    return evaluate_rpn(shunting_yard(list(element)), calculator)


def _eval_paren_token(par_tok, calculator: Calculator) -> CalcValue:
    """ParenToken -> CalcValue.

    Dispatches per ParenKind: Bracket -> Collection.List, Paren -> Collection.Point,
    Brace -> grouping (arity-1 only). arity-1 of any kind demotes to inner eval.
    has_close=False (unclosed) does NOT block eval: an unclosed paren still
    carries valid content (grouping value, Collection elements). Hot-eval keeps
    working as the user types. Stray closes (has_open=False) are filtered out
    by evaluate_rpn before reaching here.
    """
    arity = len(par_tok.elements)
    kind = par_tok.kind

    if arity == 1:
        v = _eval_element(par_tok.elements[0], calculator)
        # arity-1 (no top-level comma) is grouping: "(x)" == "x" for any x.
        # Transparent for scalars AND collections, so "mean([1,2,3])" works like
        # "mean[1,2,3]". Only Bracket "[X]" is a real 1-element List literal with
        # its own demote/wrap policy.
        if isinstance(v, calc_native.Collection) and kind == calc_native.ParenKind.Bracket:
            if v.kind == calc_native.Collection.Kind.List:
                raise_error(ErrorKind.INVALID, "List of List not allowed")
            return calc_native.Collection(calc_native.Collection.Kind.List, [v])
        return v

    if kind == calc_native.ParenKind.Brace:
        raise_error(ErrorKind.INVALID, "brace collection type not supported")

    if arity == 0:
        if kind == calc_native.ParenKind.Paren:
            raise_error(ErrorKind.INVALID, "empty Point")
        return calc_native.Collection(calc_native.Collection.Kind.List, [])

    # Inline Rational scalarization in the hot loop: Collection storage has no
    # Rational arm. Int Rationals collapse to int, fractional become double.
    #
    # Validation:
    # - Paren (Point) items must be pure scalars; any nested Collection is rejected.
    # - Bracket (List) items must be uniform: either all scalars or all Points.
    #   Nested List is always rejected (no List-of-List).
    #
    # TODO: Fix Calculator (int, int) returning Rational(n, 1) instead of int.
    Rational = calc_native.Rational
    items = []
    expected = None  # None | "scalar" | "point"
    for e in par_tok.elements:
        v = _eval_element(e, calculator)
        if isinstance(v, Rational):
            v = v.numerator if v.denominator == 1 else v.to_double()

        if isinstance(v, calc_native.Collection):
            if kind == calc_native.ParenKind.Paren:
                raise_error(ErrorKind.INVALID, "Point item cannot be a collection")
            # kind == Bracket here (Brace rejected before this loop).
            if v.kind == calc_native.Collection.Kind.List:
                raise_error(ErrorKind.INVALID, "List of List not allowed")
            if expected is None:
                expected = "point"
            elif expected != "point":
                raise_error(ErrorKind.INVALID, "List cannot mix scalars and points")
        else:
            if expected is None:
                expected = "scalar"
            elif expected != "scalar":
                raise_error(ErrorKind.INVALID, "List cannot mix scalars and points")

        items.append(v)

    coll_kind = (
        calc_native.Collection.Kind.List
        if kind == calc_native.ParenKind.Bracket
        else calc_native.Collection.Kind.Point
    )
    try:
        return calc_native.Collection(coll_kind, items)
    except ValueError as e:
        raise_error(ErrorKind.INVALID, str(e))


def evaluate_rpn(
    rpn_tokens: Iterable[calc_native.Token | ValueOperand], calculator: Calculator
) -> CalcValue:
    operand_stack: List[CalcValue] = []

    for tok in rpn_tokens:
        if type(tok) is ValueOperand:
            operand_stack.append(tok.value)
            continue

        assert isinstance(tok, calc_native.Token)
        if is_number_token(tok):
            operand_stack.append(_coerce_token(tok.data.value))
            continue

        if tok.kind == calc_native.TokenKind.Latex:
            try:
                latex_tok = tok.as_latex()
                left_rpn = shunting_yard(latex_tok.left)
                right_rpn = shunting_yard(latex_tok.right)
                left_val = (
                    evaluate_rpn(left_rpn, calculator) if left_rpn else calc_native.Rational(0)
                )
                right_val = (
                    evaluate_rpn(right_rpn, calculator) if right_rpn else calc_native.Rational(0)
                )
                # Root with empty degree defaults to square root
                if latex_tok.kind == calc_native.LatexKind.Root and not right_rpn:
                    right_val = calc_native.Rational(2)

                op_spec = OP_BY_ID[latex_tok.op_id]
                func = getattr(calculator, op_spec.method)
                result = func(left_val, right_val)

                operand_stack.append(result)
                continue
            except CalculatorError:
                raise
            except Exception as e:
                raise_error(ErrorKind.INVALID, f"Parse expression token error: {e}")

        if tok.kind == calc_native.TokenKind.Paren:
            par = tok.as_paren()
            # Stray close (orphan ')' / ']' / '}' from a segment boundary): no
            # value to contribute, leave the operand stack untouched.
            if not par.has_open:
                continue
            operand_stack.append(_eval_paren_token(par, calculator))
            continue

        if tok.kind == calc_native.TokenKind.Op:
            op_tok = tok.as_op()
            spec = OP_BY_ID.get(op_tok.op_id)
            assert spec is not None
            val_a = _pop_operand(operand_stack)
            func = getattr(calculator, spec.method, None)
            assert func is not None

            if spec.arity == calc_native.OpArity.Postfix:
                operand_stack.append(func(val_a))
                continue

            if spec.arity == calc_native.OpArity.Unary:
                if spec.angle_unit:
                    from tcalc.app_state import get_app_state

                    operand_stack.append(func(val_a, get_app_state().angle_unit))
                else:
                    operand_stack.append(func(val_a))
                continue

            if spec.arity == calc_native.OpArity.Binary:
                val_b = _pop_operand(operand_stack)

                operand_stack.append(func(val_b, val_a))
                continue

        raise_error(ErrorKind.MALFORMED)

    if not operand_stack:
        raise_error(ErrorKind.MALFORMED, "Operand stack empty")
    return operand_stack[0]


def evaluate_tokens(tokens: Sequence[calc_native.Token], calculator: Calculator) -> CalcValue:
    return evaluate_rpn(shunting_yard(tokens), calculator)
