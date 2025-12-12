from __future__ import annotations


import re
from typing import Iterable, List

from .engine import Calculator, CalculatorError
from . import Operation, build_operator_table, build_operation_map

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
_OPERATOR_SYMBOLS = sorted(
    set(_OPERATORS.keys()) | {OPEN_PAREN_SYM, CLOSE_PAREN_SYM},
    key=len,
    reverse=True,
)

_NUMBER_PATTERN = re.compile(r"(?:\d+\.\d*|\d+|\.\d+)(?:[eE][+-]?\d+)?")


def _is_number_token(tok: str) -> bool:
    try:
        float(tok)
        return True
    except Exception:
        return False
    

def tokenize_string(expression: str) -> List[str]:
    """Tokenize a mathematical expression into a list of tokens."""
    if not expression:
        return []

    tokens = []
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

        if expression[i].isdigit() or expression[i] == '.':
            match = _NUMBER_PATTERN.match(expression, i)
            if match:
                tokens.append(match.group(0))
                i = match.end()
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
            tokens.append(expression[start:i])
        else:
            # Fallback: consume single character to avoid infinite loop
            tokens.append(expression[i])
            i += 1
    return tokens

def _normalize_tokens(tokens: List[str]) -> List[str]:
    # Collapse consecutive +/- into a single operator
    # Insert implicit multip

    normalized: List[str] = []
    plus_minus_set = {ADD_SYM, SUB_SYM}
    
    for tok in tokens:
        if tok in plus_minus_set and normalized and normalized[-1] in plus_minus_set:
            if normalized[-1] == SUB_SYM:
                if tok == SUB_SYM:
                    normalized[-1]=ADD_SYM
                continue
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
# Shunting Yard Algorithm
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


    i = 0
    n = len(normalized)
    while i < n:
        tok = normalized[i]
        if tok == "":
            i += 1
            continue

        # Special case: unary func + unary minus + number (e.g. √-5)
        if tok in _UNARY_CALLS and i+2 < n and normalized[i+1] == SUB_SYM and _is_number_token(normalized[i+2]):
            output.append(normalized[i+2])  # number
            output.append(NEGATE_SYM)       # unary minus
            output.append(tok)              # unary func
            i += 3
            prev_token = "unary_op"
            continue

        if _is_number_token(tok):
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
        
        # Track if this is a unary operator
        if op in _UNARY_CALLS or op == NEGATE_SYM:
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


def evaluate_rpn(rpn_tokens: Iterable[str], calculator: Calculator) -> float:
    """Evaluate a list of RPN tokens and return the result."""
    operand_stack: List[float] = []

    for tok in rpn_tokens:
        if _is_number_token(tok):
            operand_stack.append(float(tok))
            continue

        # Special handling for negate
        if tok == NEGATE_SYM:

            if not operand_stack:
                print(f"[PARSER ERROR] NEGATE requires operand, stack empty")
                raise ParseError("Malformed Expression")
            
            val = operand_stack.pop()
            operand_stack.append(-val)
            continue
        

        # Handle x² as pow(val, 2)
        if tok == Operation.SQR.symbol:
            if not operand_stack:
                print(f"[PARSER ERROR] SQR requires operand, stack empty")
                raise ParseError("Malformed Expression")
            val = operand_stack.pop()
            try:
                res = calculator.pow(val, 2)
            except CalculatorError:
                raise
            operand_stack.append(res)
            continue

        # Handle unary operators generically
        if tok in _UNARY_CALLS:
            
            if not operand_stack:
                print(f"[PARSER ERROR] Unary operator {tok} requires operand, stack empty")
                raise ParseError("Malformed Expression")
            
            val = operand_stack.pop()
            
            op_member = _UNARY_CALLS[tok]
            
            method_name = op_member.value
            
            func = getattr(calculator, method_name, None)

            if func is None:
                raise ParseError(f"Calculator missing operation: {method_name}")
            try:
                if method_name in ("sin", "cos", "tan"):
                    from ..app_state import get_app_state
                    angle_unit = get_app_state().angle_unit
                    res = func(val, angle_unit)
                else:
                    res = func(val)
            except CalculatorError:
                raise
            operand_stack.append(res)
            continue

        if tok == PERCENT_SYM:

            if not operand_stack:
                print(f"[PARSER ERROR] PERCENT requires operand, stack empty")
                raise ParseError("Malformed Expression")
            
            val = operand_stack.pop()
            operand_stack.append(calculator.div(val, 100.0))
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


def evaluate_tokens(tokens: Iterable[str], calculator: Calculator) -> float:
    """Parse and evaluate tokens, returning the result."""
    rpn = shunting_yard(tokens)
    return evaluate_rpn(rpn, calculator)
