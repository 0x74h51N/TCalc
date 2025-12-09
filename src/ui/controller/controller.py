from __future__ import annotations

from typing import Callable, Dict, List, Optional

from src.core import Calculator, Operation, CalculatorError
from ..display.display import Display
from .utils import parse_entry, format_result


class CalculatorController:
    def __init__(self, calculator: Calculator, display: Display) -> None:
        self._calculator = calculator
        self._display = display

        self._entry_text: str = ""
        self._entry_clean = True
        self._just_solved = False
        self._error_text: Optional[str] = None
        self._expression_tokens: List[str] = []

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

        self._operator_symbol_values = {op.symbol for op in Operation if getattr(op, "symbol", None)}

        # parser will be used for full-expression evaluation
        from src.core.parser import evaluate_tokens
        self._evaluate_tokens = evaluate_tokens

        self._refresh_display()

    def handle_key(self, label: str, operation: Operation) -> None:
        handler = self._handlers.get(operation)
        if handler is None:
            return
        handler(label)
        self._refresh_display()

    # -- Handlers ---------------------------------------------------------

    def _handle_digit(self, label: str) -> None:
        if self._just_solved:
            self._begin_new_expression()

        if self._entry_clean or self._entry_text == "0":
            self._entry_text = label
        else:
            self._entry_text += label
        self._entry_clean = False

    def _handle_dot(self) -> None:
        if self._just_solved:
            self._begin_new_expression()

        if "." not in self._entry_text:
            if self._entry_clean:
                self._entry_text = "0."
            else:
                self._entry_text += "."
            self._entry_clean = False

    def _set_operator(self, label: str) -> None:
        # commit current entry then append operator
        self._append_current_entry()
        symbol = label

        self._expression_tokens.append(symbol)

        self._reset_entry()
        self._just_solved = False

    def _handle_equals(self) -> None:
        self._append_current_entry()
    
        if not self._expression_tokens:
            return
        try:
            value = self._evaluate_tokens(self._expression_tokens, self._calculator)
        except CalculatorError as exc:
            self._error_text = str(exc)
            return
        formatted = format_result(value)

        self._entry_text = formatted
        self._expression_tokens.clear()

        self._entry_clean = True
        self._just_solved = False

    def _handle_clear(self) -> None:
        self._reset_entry()
        self._just_solved = False
        self._expression_tokens.clear()


    def _handle_all_clear(self) -> None:
        self._reset_entry()
        self._just_solved = False
        self._expression_tokens.clear()
        #TODO history and memory will reset

    def _handle_negate(self) -> None:
        # Minimal string toggle: add/remove leading '-' on the current entry.
        if not self._entry_text:
            return
        self._entry_text = self._entry_text[1:] if self._entry_text.startswith("-") else "-" + self._entry_text
        self._entry_clean = False


    # -- Helpers ----------------------------------------------------------

    def _reset_entry(self) -> None:
        self._entry_text = ""
        self._entry_clean = True

    def _begin_new_expression(self) -> None:
        self._reset_entry()
        self._expression_tokens.clear()
        self._just_solved = False

    # expression-based evaluation now handled by parser; per-operator
    # incremental evaluation is no longer used.

    def _append_current_entry(self) -> None:
        if self._entry_text == "" and self._entry_clean:
            return

        formatted = format_result(parse_entry(self._entry_text))
        if not self._expression_tokens:
            self._expression_tokens.append(formatted)
        else:
            last = self._expression_tokens[-1]
            if last in self._operator_symbol_values:
                self._expression_tokens.append(formatted)
            else:
                self._expression_tokens[-1] = formatted
        self._entry_clean = True

    def _compose_expression(self) -> str:
        parts = list(self._expression_tokens)
        if (not self._entry_clean) or not parts or parts[-1] in self._operator_symbol_values:
            if self._entry_text:
                parts.append(self._entry_text)
        return "".join(parts).strip()

    def _preview_result(self) -> str:
        # Build token list: expression tokens plus current entry (if any)
        # If we just solved, don't show preview (result is already shown in expression)
        if self._just_solved:
            return ""

        tokens = list(self._expression_tokens)
        if (not self._entry_clean) and self._entry_text:
            tokens.append(self._entry_text)

        if not tokens or (tokens[-1] in self._operator_symbol_values and tokens[-1] != Operation.PERCENT.symbol):
            return ""

        try:
            value = self._evaluate_tokens(tokens, self._calculator)
            return format_result(value)
        except CalculatorError as exc:
            return str(exc)

    def _refresh_display(self) -> None:
        if self._error_text is not None:
            self._display.update("", self._error_text)
            self._error_text = None
            return

        expression = self._compose_expression()
        result = self._preview_result()
        self._display.update(expression, result)
