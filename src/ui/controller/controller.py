from __future__ import annotations

from typing import Callable, Dict, List, Optional

from src.core import Calculator, Operation, CalculatorError
from src.core.ops import get_symbols_with_aliases
from ..display.display import Display
from .utils import format_result


class CalculatorController:
    def __init__(self, calculator: Calculator, display: Display) -> None:
        self._calculator = calculator
        self._display = display

        self._display.expression_changed.connect(self._on_expression_input)

        self._expression: str = ""
        self._result: str = ""
        self._just_solved = False
        self._error_text: Optional[str] = None
        
        self._handlers: Dict[Operation, Callable[[str], None]] = {
            Operation.DIGIT: self._handle_digit,
            Operation.DOT: lambda _: self._handle_dot(),
            Operation.ADD: self._set_operator,
            Operation.SUB: self._set_operator,
            Operation.MUL: self._set_operator,
            Operation.DIV: self._set_operator,
            Operation.PERCENT: self._set_operator,
            Operation.OPEN_PAREN: self._set_operator,
            Operation.CLOSE_PAREN: self._set_operator,
            Operation.EQUALS: lambda _: self._handle_equals(),
            Operation.CLEAR: lambda _: self._handle_clear(),
            Operation.ALL_CLEAR: lambda _: self._handle_all_clear(),
            Operation.NEGATE: lambda _: self._handle_negate(),
        }

        # Get all operator symbols including aliases
        self._operator_symbol_values = get_symbols_with_aliases(
            lambda op: getattr(op, "symbol", None) is not None
        )
        
        # Get unary operator symbols
        self._unary_operator_symbols = get_symbols_with_aliases(
            lambda op: getattr(op, "arity", None) == "unary"
        )

        from src.core.parser import evaluate_tokens, tokenize_string
        self._evaluate_tokens = evaluate_tokens
        self._tokenize_string = tokenize_string
        
        self._compute_and_update()

    def handle_key(self, label: str, operation: Operation) -> None:
        handler = self._handlers.get(operation)
        if handler is None:
            return
        handler(label)
        self._compute_and_update()

    # -- Handlers ---------------------------------------------------------

    def _handle_digit(self, label: str) -> None:
        if self._just_solved:
            self._expression = label
            self._just_solved = False
        else:
            self._expression += label

    def _handle_dot(self) -> None:
        if self._just_solved:
            self._expression = "0."
            self._just_solved = False
        elif "." not in self._expression:
            self._expression += "."

    def _set_operator(self, label: str) -> None:
        self._expression += label
        self._just_solved = False

    def _handle_equals(self) -> None:
        tokens = self._tokenize_expression()
        if not tokens or not self._can_compute_preview(tokens):
            return
        
        try:
            value = self._evaluate_tokens(tokens, self._calculator)
        except CalculatorError as exc:
            self._error_text = str(exc)
            return
        
        formatted = format_result(value)
        self._expression = formatted
        self._just_solved = True

    def _handle_clear(self) -> None:
        self._expression = ""
        self._just_solved = False

    def _handle_all_clear(self) -> None:
        self._expression = ""
        self._just_solved = False

    def _handle_negate(self) -> None:
        if not self._expression:
            self._expression = Operation.SUB.symbol
            return
        
        tokens = self._tokenize_expression()
        
        for i in range(len(tokens) - 1, -1, -1):
            tok = tokens[i]
            # Skip operators and empty tokens
            if not tok or tok in self._operator_symbol_values:
                continue
            
            # Determine if previous token is unary minus attached to this number
            unary_prev = False
            if i > 0 and tokens[i - 1] == Operation.SUB.symbol:
                # Unary context when start of expression or previous token is operator or open paren
                if i == 1:
                    unary_prev = True
                else:
                    prev_prev = tokens[i - 2]
                    unary_prev = prev_prev in self._operator_symbol_values or prev_prev == Operation.OPEN_PAREN.symbol
            
            if unary_prev:
                tokens.pop(i - 1)
            else:
                tokens.insert(i, Operation.SUB.symbol)
            
            self._expression = "".join(tokens)
            return
        
        # No number found
        self._expression = Operation.SUB.symbol + self._expression


    # -- Helpers ----------------------------------------------------------

    def _tokenize_expression(self) -> List[str]:
        return self._tokenize_string(self._expression)

    def _can_compute_preview(self, tokens: List[str]) -> bool:
        if len(tokens) < 2:
            return False
        
        # Unary operators handling
        if len(tokens) == 2:
            return tokens[0] in self._unary_operator_symbols
        
   
        # If last token is operator and has res, show res
        last_is_operator = tokens[-1] in self._operator_symbol_values and tokens[-1] != Operation.PERCENT.symbol
        if last_is_operator:
            return self._result != ""
        
        # Check last token is valid
        return tokens[-1] not in self._operator_symbol_values or tokens[-1] == Operation.PERCENT.symbol

    def _compute_preview(self, tokens: List[str]) -> str:
        #Evaluate tokens and return formatted result

        if not self._can_compute_preview(tokens):
            return ""
        
        # If last token is operator return cached result
        last_is_operator = tokens[-1] in self._operator_symbol_values and tokens[-1] != Operation.PERCENT.symbol
        if last_is_operator:
            if last_is_operator and len(tokens) >= 3:
                result_tokens = tokens[:-1]
                try:
                    value = self._evaluate_tokens(result_tokens, self._calculator)
                    self._result = format_result(value)
                    return self._result
                except:
                    return ""
        
        try:
            value = self._evaluate_tokens(tokens, self._calculator)
            formatted = format_result(value)
            self._result = formatted
            return formatted
        except CalculatorError as exc:
            return str(exc)

    def _on_expression_input(self, text: str) -> None:
        #Handle keyboard input
        self._expression = text
        self._just_solved = False
        self._compute_and_update()

    def _compute_and_update(self) -> None:
        if self._error_text is not None:
            self._display.update_res(self._error_text)
            self._error_text = None
            return

        tokens = self._tokenize_expression()
        self._result = self._compute_preview(tokens)
        
        self._display.update_expr(self._expression)
        self._display.update_res(self._result)