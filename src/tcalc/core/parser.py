from __future__ import annotations

from typing import Iterable, List

import calc_native

from tcalc.core.errors import ErrorKind, raise_error

from .constants import CONSTANTS
from .engine import Calculator
from .ops import OP_BY_ID
from .utils import is_number_token, parse_number_token


def tokenize_string(expression: str) -> List[object]:
    return list(calc_native.tokenize_string(expression))


def shunting_yard(tokens: Iterable[object]) -> List[object]:
    return list(calc_native.shunting_yard(tokens))


def _pop_operand(operand_stack: List[object], tok: str) -> object:
    if not operand_stack:
        raise_error(ErrorKind.MALFORMED, "Pop operand, not operand in stack.")
    return operand_stack.pop()


def _coerce_token(tok: object) -> object:
    if isinstance(tok, str):
        if tok in CONSTANTS:
            return CONSTANTS[tok]
        try:
            return parse_number_token(tok)
        except Exception as e:
            raise_error(ErrorKind.INVALID, f"Parse number token error: {e}")
    return tok


def evaluate_rpn(rpn_tokens: Iterable[object], calculator: Calculator) -> object:
    operand_stack: List[object] = []

    for tok in rpn_tokens:
        if is_number_token(tok):
            operand_stack.append(_coerce_token(tok.value))
            continue
        if tok.kind == calc_native.TokenKind.Op:
            spec = OP_BY_ID.get(tok.op_id)

        if spec.arity == "postfix":
            val = _pop_operand(operand_stack, spec.sym)
            func = getattr(calculator, spec.method, None)

            operand_stack.append(func(val))
            continue

        if spec.arity == "unary":
            val = _pop_operand(operand_stack, spec.sym)
            func = getattr(calculator, spec.method, None)

            if spec.needs_unit:
                from tcalc.app_state import get_app_state

                operand_stack.append(func(val, get_app_state().angle_unit))
            else:
                operand_stack.append(func(val))
            continue

        if spec.arity == "binary":
            if len(operand_stack) < 2:
                raise_error(
                    ErrorKind.MALFORMED,
                    "Operand stack length less than 2, spec.arity: binary",
                )
            b = operand_stack.pop()
            a = operand_stack.pop()
            func = getattr(calculator, spec.method, None)

            operand_stack.append(func(a, b))
            continue

        raise_error(ErrorKind.MALFORMED)

    return operand_stack[0]


def evaluate_tokens(tokens: Iterable[object], calculator: Calculator) -> object:
    return evaluate_rpn(shunting_yard(tokens), calculator)
