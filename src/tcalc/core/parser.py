#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from typing import Iterable, List, Sequence

import calc_native

from tcalc.errors import CalculatorError, ErrorKind, Msg, raise_error

from .constants import CONST_BY_ID, CONST_VALUES
from .engine import Calculator
from .ops import OP_BY_ID
from .utils import CalcValue, is_number_token, parse_number_token
from .varstore import VarStore


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
        raise_error(ErrorKind.MALFORMED, Msg.POP_OPERAND)
    return operand_stack.pop()


def _resolve_name(name: str, env: VarStore) -> CalcValue:
    v = env.get(name)
    if v is not None:
        return v
    raise_error(ErrorKind.INVALID, Msg.undefined_variable(name))


def _subscript_name(latex) -> str | None:
    """LatexToken(Subscript) -> variable name 'base_sub', or None if the base
    is not a single letter (a non-identifier base is not a variable name)."""
    left = latex.left
    if len(left) != 1 or left[0].kind != calc_native.TokenKind.Char:
        return None
    return f"{left[0].as_char().value}_{calc_native.tokens_to_flat_text(latex.right)}"


def _coerce_token(tok: str | int | float) -> CalcValue:
    if isinstance(tok, str):
        try:
            return parse_number_token(tok)
        except Exception as e:
            raise_error(ErrorKind.INVALID, Msg.parse_number_error(e))
    if isinstance(tok, int):
        return calc_native.Rational(tok)
    return tok


def _eval_element(element, calculator: Calculator, env: VarStore) -> CalcValue:
    """Element (arm 0 Token OR arm 1 list[Token]) -> CalcValue.

    Fast-paths arm 0 NumberToken (direct _coerce_token) and arm 0 ParenToken
    (direct _eval_paren_token recursion) to skip wrapping + shunting_yard +
    evaluate_rpn unnecessarily. Latex, Call, and multi-token arm 1 paths go
    through evaluate_rpn so TokenKind dispatch stays single-sourced there.
    """
    if isinstance(element, calc_native.Token):
        kind = element.kind
        if kind == calc_native.TokenKind.Number:
            return _coerce_token(element.data.value)
        if kind == calc_native.TokenKind.Char:
            return _resolve_name(element.as_char().value, env)
        if kind == calc_native.TokenKind.Const:
            return CONST_VALUES[element.as_const().id]
        if kind == calc_native.TokenKind.Paren:
            return _eval_paren_token(element.as_paren(), calculator, env)
        if kind == calc_native.TokenKind.Latex:
            return evaluate_rpn([element], calculator, env)
        if kind == calc_native.TokenKind.Call:
            return evaluate_rpn([element], calculator, env)
        raise_error(ErrorKind.INVALID, Msg.element_kind(kind))

    if not element:
        raise_error(ErrorKind.INVALID, Msg.EMPTY_ELEMENT)
    return evaluate_rpn(shunting_yard(list(element)), calculator, env)


def _eval_elements(elements, kind, calculator: Calculator, env: VarStore) -> CalcValue:
    """elements (ParenToken.elements OR CallToken.args) + ParenKind -> CalcValue.

    Dispatches per ParenKind: Bracket -> Collection.List, Paren -> Collection.Point,
    Brace -> grouping (arity-1 only). arity-1 of any kind demotes to inner eval.
    Shared by ParenToken eval and Call eval (call-paren args have identical
    comma-split/element shape to a Paren-kind ParenToken's elements).
    """
    arity = len(elements)

    if arity == 1:
        v = _eval_element(elements[0], calculator, env)
        # arity-1 (no top-level comma) is grouping: "(x)" == "x" for any x.
        # Transparent for scalars AND collections, so "mean([1,2,3])" works like
        # "mean[1,2,3]". Only Bracket "[X]" is a real 1-element List literal with
        # its own demote/wrap policy.
        if isinstance(v, calc_native.Collection) and kind == calc_native.ParenKind.Bracket:
            if v.kind == calc_native.Collection.Kind.List:
                raise_error(ErrorKind.INVALID, Msg.LIST_OF_LIST)
            return calc_native.Collection(calc_native.Collection.Kind.List, [v])
        return v

    if kind == calc_native.ParenKind.Brace:
        raise_error(ErrorKind.INVALID, Msg.BRACE_UNSUPPORTED)

    if arity == 0:
        if kind == calc_native.ParenKind.Paren:
            raise_error(ErrorKind.INVALID, Msg.EMPTY_POINT)
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
    for e in elements:
        v = _eval_element(e, calculator, env)
        if isinstance(v, Rational):
            v = v.numerator if v.denominator == 1 else v.to_double()

        if isinstance(v, calc_native.Collection):
            if kind == calc_native.ParenKind.Paren:
                raise_error(ErrorKind.INVALID, Msg.POINT_ITEM_COLLECTION)
            # kind == Bracket here (Brace rejected before this loop).
            if v.kind == calc_native.Collection.Kind.List:
                raise_error(ErrorKind.INVALID, Msg.LIST_OF_LIST)
            if expected is None:
                expected = "point"
            elif expected != "point":
                raise_error(ErrorKind.INVALID, Msg.LIST_MIX)
        else:
            if expected is None:
                expected = "scalar"
            elif expected != "scalar":
                raise_error(ErrorKind.INVALID, Msg.LIST_MIX)

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


def _eval_paren_token(par_tok, calculator: Calculator, env: VarStore) -> CalcValue:
    """ParenToken -> CalcValue.

    has_close=False (unclosed) does NOT block eval: an unclosed paren still
    carries valid content (grouping value, Collection elements). Hot-eval keeps
    working as the user types. Stray closes (has_open=False) are filtered out
    by evaluate_rpn before reaching here.
    """
    return _eval_elements(par_tok.elements, par_tok.kind, calculator, env)


def _eval_call_dataset(args, calculator: Calculator, env: VarStore) -> CalcValue:
    # Variadic call args -> a List dataset. A lone collection is the dataset;
    # a lone scalar wraps as List([v]); N args reuse the Bracket list rule.
    if len(args) == 1:
        v = _eval_element(args[0], calculator, env)
        if isinstance(v, calc_native.Collection):
            return v
        if isinstance(v, calc_native.Rational):
            v = v.numerator if v.denominator == 1 else v.to_double()
        return calc_native.Collection(calc_native.Collection.Kind.List, [v])
    return _eval_elements(args, calc_native.ParenKind.Bracket, calculator, env)


def evaluate_rpn(
    rpn_tokens: Iterable[calc_native.Token | ValueOperand],
    calculator: Calculator,
    env: VarStore | None = None,
) -> CalcValue:
    if env is None:
        env = VarStore()
    operand_stack: List[CalcValue] = []

    for tok in rpn_tokens:
        if type(tok) is ValueOperand:
            operand_stack.append(tok.value)
            continue

        assert isinstance(tok, calc_native.Token)
        if is_number_token(tok):
            operand_stack.append(_coerce_token(tok.data.value))
            continue

        if tok.kind == calc_native.TokenKind.Char:
            operand_stack.append(_resolve_name(tok.as_char().value, env))
            continue

        if tok.kind == calc_native.TokenKind.Const:
            operand_stack.append(CONST_VALUES[tok.as_const().id])
            continue

        if tok.kind == calc_native.TokenKind.Latex:
            latex_tok = tok.as_latex()
            if latex_tok.kind == calc_native.LatexKind.Subscript:
                name = _subscript_name(latex_tok)
                if name is None:
                    name = (
                        calc_native.tokens_to_flat_text(latex_tok.left)
                        + "_"
                        + calc_native.tokens_to_flat_text(latex_tok.right)
                    )
                operand_stack.append(_resolve_name(name, env))
                continue
            try:
                left_rpn = shunting_yard(latex_tok.left)
                right_rpn = shunting_yard(latex_tok.right)
                left_val = (
                    evaluate_rpn(left_rpn, calculator, env) if left_rpn else calc_native.Rational(0)
                )
                right_val = (
                    evaluate_rpn(right_rpn, calculator, env)
                    if right_rpn
                    else calc_native.Rational(0)
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
                raise_error(ErrorKind.INVALID, Msg.parse_expression_error(e))

        if tok.kind == calc_native.TokenKind.Call:
            call = tok.as_call()
            spec = OP_BY_ID.get(call.op_id)
            assert spec is not None
            func = getattr(calculator, spec.method)
            if spec.is_variadic:
                operand_stack.append(func(_eval_call_dataset(call.args, calculator, env)))
                continue
            n = spec.call_arity
            if len(call.args) != n:
                raise_error(ErrorKind.INVALID, Msg.takes_arguments(spec.symbol, n))
            arg_vals = [_eval_element(a, calculator, env) for a in call.args]
            if any(isinstance(v, calc_native.Collection) for v in arg_vals):
                raise_error(ErrorKind.INVALID, Msg.not_for_list_or_point(spec.symbol))
            if spec.angle_unit:
                from tcalc.app_state import get_app_state

                operand_stack.append(func(*arg_vals, get_app_state().angle_unit))
            else:
                operand_stack.append(func(*arg_vals))
            continue

        if tok.kind == calc_native.TokenKind.Paren:
            par = tok.as_paren()
            # Stray close (orphan ')' / ']' / '}' from a segment boundary): no
            # value to contribute, leave the operand stack untouched.
            if not par.has_open:
                continue
            operand_stack.append(_eval_paren_token(par, calculator, env))
            continue

        if tok.kind == calc_native.TokenKind.Op:
            op_tok = tok.as_op()
            spec = OP_BY_ID.get(op_tok.op_id)
            assert spec is not None
            if spec.id == calc_native.OpId.Assign:
                raise_error(ErrorKind.INVALID, Msg.INVALID_ASSIGNMENT)
            # Fixed-arity (>= 2) call functions have no infix form and need
            # their parentheses; typed bare they reach here as an Op token with
            # too few operands. Variadic ops (e.g. min[1,2,3]) validly apply to
            # a following collection operand, so they are not rejected here.
            if not spec.is_variadic and spec.call_arity != 1:
                raise_error(ErrorKind.INVALID, Msg.needs_call_form(spec.symbol))
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
        raise_error(ErrorKind.MALFORMED, Msg.OPERAND_STACK_EMPTY)
    return operand_stack[0]


def evaluate_tokens(
    tokens: Sequence[calc_native.Token], calculator: Calculator, env: VarStore | None = None
) -> CalcValue:
    if env is None:
        env = VarStore()
    if (
        len(tokens) >= 2
        and tokens[1].kind == calc_native.TokenKind.Op
        and tokens[1].as_op().op_id == calc_native.OpId.Assign
    ):
        first = tokens[0]
        if first.kind == calc_native.TokenKind.Char:
            name = first.as_char().value
        elif (
            first.kind == calc_native.TokenKind.Latex
            and first.as_latex().kind == calc_native.LatexKind.Subscript
        ):
            sub_name = _subscript_name(first.as_latex())
            if sub_name is None:
                raise_error(ErrorKind.INVALID, Msg.INVALID_ASSIGNMENT_TARGET)
            name = sub_name
        else:
            if first.kind == calc_native.TokenKind.Op:
                spec = OP_BY_ID.get(first.as_op().op_id)
                raise_error(
                    ErrorKind.INVALID,
                    Msg.assignment_target_is_operator(
                        spec.symbol if spec else str(first.as_op().op_id)
                    ),
                )
            if first.kind == calc_native.TokenKind.Const:
                cspec = CONST_BY_ID.get(first.as_const().id)
                raise_error(
                    ErrorKind.INVALID,
                    Msg.assignment_target_is_constant(
                        cspec.symbol if cspec else str(first.as_const().id)
                    ),
                )
            raise_error(ErrorKind.INVALID, Msg.INVALID_ASSIGNMENT_TARGET)
        rhs = list(tokens[2:])
        if not rhs:
            raise_error(ErrorKind.INVALID, Msg.EMPTY_ASSIGNMENT)
        value = evaluate_rpn(shunting_yard(rhs), calculator, env)
        env.set(name, value)
        return value
    return evaluate_rpn(shunting_yard(tokens), calculator, env)
