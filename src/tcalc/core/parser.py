from __future__ import annotations


import re
from typing import Iterable, List

from .engine import Calculator, CalculatorError
from . import Operation, build_operator_table, build_operation_map
from .utils import is_number_token, parse_number_token
from .constants import CONSTANTS

try:
    import calc_native  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    calc_native = None


ADD_SYM = Operation.ADD.symbol
SUB_SYM = Operation.SUB.symbol
MUL_SYM = Operation.MUL.symbol
DIV_SYM = Operation.DIV.symbol
PERCENT_SYM = Operation.PERCENT.symbol
OPEN_PAREN_SYM = Operation.OPEN_PAREN.symbol
CLOSE_PAREN_SYM = Operation.CLOSE_PAREN.symbol
NEGATE_SYM = Operation.NEGATE.symbol


class ParseError(CalculatorError):
    """Exception raised for expression parsing errors."""
    pass


# Build operator tables
_OPERATORS = build_operator_table(lambda op: op.precedence is not None)
_OP_CALLS = build_operation_map(lambda op: op.arity == "binary")
_UNARY_CALLS = build_operation_map(lambda op: op.arity == "unary")
_POSTFIX_CALLS = build_operation_map(lambda op: op.arity == "postfix")
_OPERATOR_SYMBOLS = sorted(
    set(_OPERATORS.keys()) | {OPEN_PAREN_SYM, CLOSE_PAREN_SYM},
    key=len,
    reverse=True,
)

_NUMBER_PATTERN = re.compile(r"(?:\d+\.\d*|\d+|\.\d+)(?:[eE][+-]?\d+)?")



def tokenize_string(expression: str) -> List[object]:
    """Tokenize a mathematical expression into a list of tokens."""
    if not expression:
        return []

    tokens: List[object] = []
    i = 0
    length = len(expression)
    
    while i < length:
        if expression[i].isspace():
            i += 1
            continue
        
        symbol = None
        for op in _OPERATOR_SYMBOLS:
            if expression.startswith(op, i):
                symbol = op
                break
        
        if symbol:
            tokens.append(symbol)
            i += len(symbol)
            continue

        if expression[i].isdigit() or expression[i] == ".":
            match = _NUMBER_PATTERN.match(expression, i)
            if match:
                number_token = parse_number_token(match.group(0))
                j = match.end()
                if j < length and expression[j] in {"i", "I"}:
                    coef = float(str(number_token)) if calc_native is not None and isinstance(number_token, getattr(calc_native, "BigReal", ())) else float(number_token)
                    tokens.append(complex(0.0, coef))
                    i = j + 1
                else:
                    tokens.append(number_token)
                    i = j
                continue
        
        start = i
        while i < length:
            if expression[i].isspace():
                break
            # stop when an operator begins at current position
            begins_operator = any(expression.startswith(op, i) for op in _OPERATOR_SYMBOLS)
            if begins_operator:
                break
            i += 1
        if start != i:
            ident = expression[start:i]
            constant = CONSTANTS.get(ident)
            if constant is None:
                constant = CONSTANTS.get(ident.lower())
            tokens.append(constant if constant is not None else ident)
        else:
            # Fallback: consume single character to avoid infinite loop
            tokens.append(expression[i])
            i += 1
    return tokens

def _normalize_tokens(tokens: List[object]) -> List[object]:
    # Collapse consecutive +/- into a single operator
    # Insert implicit multip

    normalized: List[object] = []
    plus_minus_set = {ADD_SYM, SUB_SYM}

    for tok in tokens:
        if isinstance(tok, str) and tok in plus_minus_set and normalized and isinstance(normalized[-1], str) and normalized[-1] in plus_minus_set:
            if normalized[-1] == SUB_SYM:
                if tok == SUB_SYM:
                    normalized[-1]=ADD_SYM
                continue
            else:
                normalized[-1] = tok
        else:
            if normalized:
                last = normalized[-1]
                last_ends_operand = is_number_token(last) or last == CLOSE_PAREN_SYM or (isinstance(last, str) and last in _POSTFIX_CALLS)
                tok_starts_operand = (
                    is_number_token(tok)
                    or tok == OPEN_PAREN_SYM
                    or tok == NEGATE_SYM
                    or (isinstance(tok, str) and tok in _UNARY_CALLS)
                )
                if last_ends_operand and tok_starts_operand:
                    normalized.append(MUL_SYM)
            normalized.append(tok)

    return normalized

#
# Shunting Yard Algorithm
# RIP Edsger Dijkstra
#
# Ref: https://www.sunshine2k.de/articles/coding/shuntingyardalgorithm/shunting_yard_algorithm.html
#
def shunting_yard(tokens: Iterable[object]) -> List[object]:

    token_list = list(tokens)

    normalized = _normalize_tokens(token_list)
    
    output: List[object] = []
    operator_stack: List[str] = []

    prev_token = None


    i = 0
    n = len(normalized)
    while i < n:
        tok = normalized[i]
        if tok == "":
            i += 1
            continue

        # Special case: unary func + unary minus + number (e.g. √-5)
        if (
            isinstance(tok, str)
            and tok in _UNARY_CALLS
            and i + 2 < n
            and normalized[i + 1] == SUB_SYM
            and is_number_token(normalized[i + 2])
        ):
            output.append(normalized[i+2])  # number
            output.append(NEGATE_SYM)       # unary minus
            output.append(tok)              # unary func
            i += 3
            prev_token = "unary_op"
            continue

        if is_number_token(tok):
            output.append(tok)
            prev_token = "number"
            i += 1
            continue

        if tok == OPEN_PAREN_SYM:
            operator_stack.append(tok)
            prev_token = OPEN_PAREN_SYM
            i += 1
            continue

        if tok == CLOSE_PAREN_SYM:
            while operator_stack and operator_stack[-1] != OPEN_PAREN_SYM:
                output.append(operator_stack.pop())
            if operator_stack and operator_stack[-1] == OPEN_PAREN_SYM:
                operator_stack.pop()
            prev_token = CLOSE_PAREN_SYM
            i += 1
            continue

        # operator
        # determine unary minus (after unary ops, at start, after binary ops, or after open paren)
        if tok == SUB_SYM:
            if prev_token is None or prev_token in (OPEN_PAREN_SYM, "op", "unary_op"):
                op = NEGATE_SYM
            else:
                op = "-"
        else:
            op = tok

        if op not in _OPERATORS:
            print(f"Unknown operator: {op}")
            raise ParseError(f"Syntax Error")

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
        
        # Track if this operator starts/ends an operand, for unary-minus disambiguation
        if op in _POSTFIX_CALLS:
            prev_token = "number"
        elif op in _UNARY_CALLS or op == NEGATE_SYM:
            prev_token = "unary_op"
        else:
            prev_token = "op"
        i += 1

    while operator_stack:
        top = operator_stack.pop()

        if top in (OPEN_PAREN_SYM, CLOSE_PAREN_SYM):
            continue

        output.append(top)

    return output


def _pop_operand(operand_stack: List[object], tok: str) -> object:
    if not operand_stack:
        print(f"[PARSER ERROR] Operator {tok} requires operand, stack empty")
        raise ParseError("Malformed Expression")
    return operand_stack.pop()


def evaluate_rpn(rpn_tokens: Iterable[object], calculator: Calculator) -> object:
    """Evaluate a list of RPN tokens and return the result."""
    operand_stack: List[object] = []

    for tok in rpn_tokens:
        if is_number_token(tok):
            operand_stack.append(tok)
            continue

        if tok in _POSTFIX_CALLS:
            val = _pop_operand(operand_stack, tok)
            op_member = _POSTFIX_CALLS[tok]

            func = getattr(calculator, op_member.value, None)
            if func is None:
                raise ParseError(f"Calculator missing operation: {op_member.value}")

            res = func(val)
            operand_stack.append(res)
            continue

        # Handle unary operators generically
        if tok in _UNARY_CALLS:
            val = _pop_operand(operand_stack, tok)
            op_member = _UNARY_CALLS[tok]

            try:
                if op_member in (
                    Operation.SIN,
                    Operation.COS,
                    Operation.TAN,
                    Operation.ASIN,
                    Operation.ACOS,
                    Operation.ATAN,
                    Operation.POLAR,
                ):
                    from tcalc.app_state import get_app_state
                    
                    func = getattr(calculator, op_member.value, None)

                    if func is None:
                        raise ParseError(f"Calculator missing operation: {op_member.value}")
                    
                    res = func(val, get_app_state().angle_unit)
                else:
                    func = getattr(calculator, op_member.value, None)
                    if func is None:
                        raise ParseError(f"Calculator missing operation: {op_member.value}")
                    res = func(val)
            except CalculatorError:
                raise
            operand_stack.append(res)
            continue

        if tok in _OP_CALLS:

            if len(operand_stack) < 2:
                print(f"[PARSER ERROR] Binary operator {tok} requires 2 operands, stack has {len(operand_stack)}")
                raise ParseError("Malformed Expression")
            
            b = operand_stack.pop()
            a = operand_stack.pop()

            op_member = _OP_CALLS[tok]
            method_name = op_member.value
            
            func = getattr(calculator, method_name, None)
            
            if func is None:
                print(f"Calculator missing operation: {method_name}")
                raise ParseError("Syntax Error")


            try:
                res = func(a, b)

            except CalculatorError as e:
                print(f"[PARSER] CalculatorError: {e}")
                raise

            operand_stack.append(res)
            continue
        
        print(f"[PARSER ERROR] Unknown token in RPN: '{tok}'")
        raise ParseError(f"Malformed Expression")

    if len(operand_stack) != 1:
        print(f"[PARSER ERROR] Final stack should have 1 element, has {len(operand_stack)}: {operand_stack}")
        raise ParseError("Malformed Expression")
    
    return operand_stack[0]


def evaluate_tokens(tokens: Iterable[object], calculator: Calculator) -> object:
    """Parse and evaluate tokens, returning the result."""
    rpn = shunting_yard(tokens)
    return evaluate_rpn(rpn, calculator)
