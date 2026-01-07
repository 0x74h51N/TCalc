from __future__ import annotations

from typing import Iterable, List, Sequence

import calc_native

from tcalc.core.errors import ErrorKind, raise_error

from .constants import CONSTANTS
from .engine import Calculator
from .ops import OP_BY_ID
from .utils import is_number_token, parse_number_token


def tokenize_string(expression: str) -> List[calc_native.Token]:
    return list(calc_native.tokenize_string(expression))


def shunting_yard(tokens: Sequence[calc_native.Token]) -> List[calc_native.Token]:
    return list(calc_native.shunting_yard(tokens))


def _pop_operand(operand_stack: List[object]) -> object:
    if not operand_stack:
        raise_error(ErrorKind.MALFORMED, "Pop operand, not operand in stack.")
    return operand_stack.pop()


def _coerce_token(tok: str | int | float) -> object:
    if isinstance(tok, str):
        if tok in CONSTANTS:
            return CONSTANTS[tok]
        try:
            return parse_number_token(tok)
        except Exception as e:
            raise_error(ErrorKind.INVALID, f"Parse number token error: {e}")
    return tok


def evaluate_rpn(rpn_tokens: Iterable[calc_native.Token], calculator: Calculator) -> object:
    operand_stack: List[object] = []

    for tok in rpn_tokens:
        if is_number_token(tok):
            operand_stack.append(_coerce_token(tok.value))
            continue
        if tok.kind == calc_native.TokenKind.Op:
            spec = OP_BY_ID.get(tok.op_id)
            assert spec is not None
            val_a = _pop_operand(operand_stack)
            func = getattr(calculator, spec.method, None)
            assert func is not None

            if spec.arity == calc_native.OpArity.Postfix:
                operand_stack.append(func(val_a))
                continue

            if spec.arity == calc_native.OpArity.Unary:
                if spec.needs_unit:
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


def evaluate_tokens(tokens: Sequence[calc_native.Token], calculator: Calculator) -> object:
    return evaluate_rpn(shunting_yard(tokens), calculator)
