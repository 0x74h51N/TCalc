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


def evaluate_rpn(rpn_tokens: Iterable[calc_native.Token], calculator: Calculator) -> CalcValue:
    operand_stack: List[CalcValue] = []

    for tok in rpn_tokens:
        if is_number_token(tok):
            operand_stack.append(_coerce_token(tok.data.value))
            continue

        # Stray parens left by shunting_yard (unclosed groups) -> skip at
        if tok.kind == calc_native.TokenKind.Paren:
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
