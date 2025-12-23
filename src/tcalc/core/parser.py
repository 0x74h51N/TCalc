from __future__ import annotations

from typing import Iterable, List

import calc_native

from .constants import CONSTANTS
from .engine import Calculator, CalculatorError
from .ops import OP_BY_ID
from .utils import is_number_token, parse_number_token
import logging


#
# TODO: Make error handling more pleasent.
#

class ParseError(CalculatorError):
    pass


def tokenize_string(expression: str) -> List[object]:
    return list(calc_native.tokenize_string(expression))


def shunting_yard(tokens: Iterable[object]) -> List[object]:
    return list(calc_native.shunting_yard(tokens))


def _pop_operand(operand_stack: List[object], tok: str) -> object:
    if not operand_stack:
        raise ParseError("Malformed Expression")
    return operand_stack.pop()

def _coerce_token(tok: object) -> object:
    if isinstance(tok, str):
        if tok in CONSTANTS:
            return CONSTANTS[tok]
        try:
            return parse_number_token(tok)
        except Exception as e:
            logging.error("Invalid expression: %s", e)
            raise ParseError("Invalid expression")
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
                raise ParseError("Malformed Expression")
            b = operand_stack.pop()
            a = operand_stack.pop()
            func = getattr(calculator, spec.method, None)
            
            operand_stack.append(func(a, b))
            continue

        raise ParseError("Malformed Expression")

    return operand_stack[0]


def evaluate_tokens(tokens: Iterable[object], calculator: Calculator) -> object:
    return evaluate_rpn(shunting_yard(tokens), calculator)
