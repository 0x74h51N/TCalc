from __future__ import annotations

from typing import Iterable, List

from .engine import Calculator, CalculatorError
from .ops import Operation

ADD_SYM = Operation.ADD.symbol
SUB_SYM = Operation.SUB.symbol
MUL_SYM = Operation.MUL.symbol
DIV_SYM = Operation.DIV.symbol
PERCENT_SYM = Operation.PERCENT.symbol
OPEN_PAREN_SYM = Operation.OPEN_PAREN.symbol
CLOSE_PAREN_SYM = Operation.CLOSE_PAREN.symbol
NEGATE_SYM = Operation.NEGATE.symbol


class ParseError(CalculatorError):
    pass


# Build operator tables from ops.py
_OPERATORS: dict[str, tuple[int, str]] = {}
_OP_CALLS: dict[str, Operation] = {}

for member in Operation:
    sym = getattr(member, "symbol", None)
    if not sym:
        continue
    if getattr(member, "precedence", None) is not None:
        _OPERATORS[sym] = (member.precedence, member.associativity)
    if getattr(member, "arity", None) == "binary":
        _OP_CALLS[sym] = member


def _is_number_token(tok: str) -> bool:
    try:
        float(tok)
        return True
    except Exception:
        return False


def _normalize_tokens(tokens: List[str]) -> List[str]:
    # Collapse consecutive +/- into a single operator
    # Insert implicit multip

    normalized: List[str] = []
    plus_minus_set = {ADD_SYM, SUB_SYM}
    
    for tok in tokens:
        if tok in plus_minus_set and normalized and normalized[-1] in plus_minus_set:
            if normalized[-1] == SUB_SYM:
                continue  # Skip consecutive + after -
            else:
                normalized[-1] = tok
        else:
            # Insert implicit multip
            if normalized:
                last = normalized[-1]
                if (_is_number_token(last) or last == CLOSE_PAREN_SYM or last == PERCENT_SYM) and \
                   (_is_number_token(tok) or tok == OPEN_PAREN_SYM or tok == NEGATE_SYM):
                    normalized.append(MUL_SYM)
            normalized.append(tok)
    
    return normalized

#
# Shunting Yard Algorithm (1961): infix → RPN via two stacks
# RIP Edsger Dijkstra
#
# Ref: https://www.sunshine2k.de/articles/coding/shuntingyardalgorithm/shunting_yard_algorithm.html
#
def shunting_yard(tokens: Iterable[str]) -> List[str]:

    token_list = list(tokens)
    normalized = _normalize_tokens(token_list)
    
    output: List[str] = []
    operator_stack: List[str] = []

    prev_token = None

    for tok in normalized:
        if tok == "":
            continue
        if _is_number_token(tok):
            output.append(tok)
            prev_token = "number"
            continue

        if tok == OPEN_PAREN_SYM:
            operator_stack.append(tok)
            prev_token = CLOSE_PAREN_SYM
            continue

        if tok == CLOSE_PAREN_SYM:
            while operator_stack and operator_stack[-1] != OPEN_PAREN_SYM:
                output.append(operator_stack.pop())
       
            if operator_stack and operator_stack[-1] == OPEN_PAREN_SYM:
                operator_stack.pop()
            prev_token = CLOSE_PAREN_SYM
            continue

        # operator
        # determine unary minus
        if tok == SUB_SYM:
            if prev_token is None or prev_token in (OPEN_PAREN_SYM, "op"):
                op = NEGATE_SYM 
            else:
                op = "-"
        else:
            op = tok

        if op not in _OPERATORS:
            raise ParseError(f"Unknown operator: {op}")

        prec, assoc = _OPERATORS[op]

        while operator_stack and operator_stack[-1] != OPEN_PAREN_SYM:
            top = operator_stack[-1]
            if top not in _OPERATORS:
                break
            top_prec, _top_assoc = _OPERATORS[top]
            if (assoc == "left" and prec <= top_prec) or (assoc == "right" and prec < top_prec):
                output.append(operator_stack.pop())
            else:
                break
        operator_stack.append(op)
        prev_token = "op"

    while operator_stack:
        top = operator_stack.pop()
        if top in (OPEN_PAREN_SYM, CLOSE_PAREN_SYM):
            continue
        output.append(top)

    return output


def evaluate_rpn(rpn_tokens: Iterable[str], calculator: Calculator) -> float:

    operand_stack: List[float] = []

    for tok in rpn_tokens:
        if _is_number_token(tok):
            operand_stack.append(float(tok))
            continue

        if tok == NEGATE_SYM:
            if not operand_stack:
                raise ParseError("Malformed Expression")
            val = operand_stack.pop()
            operand_stack.append(-val)
            continue

        if tok == PERCENT_SYM:
            if not operand_stack:
                raise ParseError("Malformed Expression")
            val = operand_stack.pop()
            operand_stack.append(calculator.div(val, 100.0))
            continue

        if tok in _OP_CALLS:
            if len(operand_stack) < 2:
                raise ParseError("Malformed Expression")
            b = operand_stack.pop()
            a = operand_stack.pop()
            op_member = _OP_CALLS[tok]
            method_name = op_member.value
            func = getattr(calculator, method_name, None)
            if func is None:
                raise ParseError(f"Calculator missing operation: {method_name}")
            try:
                res = func(a, b)
            except CalculatorError:
                raise
            operand_stack.append(res)
            continue

        raise ParseError(f"Unknown token in RPN: {tok}")

    if len(operand_stack) != 1:
        raise ParseError("Malformed Expression")
    return operand_stack[0]


def evaluate_tokens(tokens: Iterable[str], calculator: Calculator) -> float:

    rpn = shunting_yard(tokens)
    return evaluate_rpn(rpn, calculator)
