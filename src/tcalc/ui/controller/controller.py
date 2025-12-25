from __future__ import annotations

from typing import Callable, Dict, List, Optional

import calc_native

from tcalc.app_state import AngleUnit, get_app_state
from tcalc.core import (
    Operation,
    evaluate_tokens,
    get_symbols_with_aliases,
    tokenize_string,
)
from tcalc.core.errors import ErrorKind
from tcalc.core.utils import is_number_token

from ..widgets.calc.topbar.defins import MEMORY_KEYS, MemoryKey
from .utils import clean_for_expression, format_result


class CalculatorController:
    """Main controller handling calculator input, expression state and display updates."""

    def __init__(self, calculator, display, history, edit_ops, topbar) -> None:
        self._calculator = calculator
        self._display = display
        self._history = history
        self._edit_ops = edit_ops
        self._topbar = topbar
        self._app_state = get_app_state()

        self._display.expression_changed.connect(self._on_expression_input)

        self._expression: str = ""
        self._result: str = ""
        self._just_solved = False
        self._error_text: Optional[str] = None
        self._force_error_display = False
        self._can_preview = False

        self._memory_ops = {str(k["operation"]) for k in MEMORY_KEYS}

        # Build handlers dictionary
        self._handlers: Dict[Operation, Callable[[str], None]] = self._build_handlers()

        # Get all operator symbols including aliases
        self._operator_symbol_values = get_symbols_with_aliases(
            lambda op: getattr(op, "sym", None) is not None
        )
        self._operator_symbol_values.discard(Operation.IMAG.symbol)

        # Get unary operator symbols
        self._unary_operator_symbols = get_symbols_with_aliases(
            lambda op: getattr(op, "arity", None) == "unary"
        )

        # Get postfix operator symbols
        self._postfix_operator_symbols = get_symbols_with_aliases(
            lambda op: getattr(op, "arity", None) == "postfix"
        )

        self._tokenize_string = tokenize_string

        self._history.set_memory("")
        self._compute_and_update()

    def handle_key(self, label: str, operation) -> None:
        """Dispatch button press to appropriate handler."""

        if operation == "shift":
            self._app_state.shifted = not self._app_state.shifted
            self._compute_and_update()
            return

        if isinstance(operation, str) and operation in self._memory_ops:
            self._handle_memory(operation)
            self._compute_and_update()
            return

        if not isinstance(operation, Operation):
            self._handle_digit(label)
            self._compute_and_update()
            return

        if self._app_state.hyp and operation in (
            Operation.SIN,
            Operation.COS,
            Operation.TAN,
            Operation.ASIN,
            Operation.ACOS,
            Operation.ATAN,
        ):
            operation = {
                Operation.SIN: Operation.SINH,
                Operation.COS: Operation.COSH,
                Operation.TAN: Operation.TANH,
                Operation.ASIN: Operation.ASINH,
                Operation.ACOS: Operation.ACOSH,
                Operation.ATAN: Operation.ATANH,
            }[operation]
            label = operation.symbol

        handler = self._handlers.get(operation)

        handler(label)
        self._compute_and_update()

    # -- Handlers ---------------------------------------------------------

    def _handle_digit(self, label: str) -> None:
        """Append digit to expression, reset if just solved."""
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

    def _set_operator(self, _label: str, operation: Operation) -> None:
        symbol = operation.symbol
        arity = getattr(operation, "arity", None)
        if arity == "unary":
            self._expression += f"{symbol}{Operation.OPEN_PAREN.symbol}"
        elif arity == "binary":
            self._expression += f" {symbol} "
        else:
            self._expression += symbol
        self._just_solved = False

    def _evaluate_tokens(self, tokens, calculator):
        """Call core.evaluate_tokens; on CalculatorError log and return the error text."""
        try:
            return evaluate_tokens(tokens, calculator)
        except Exception as exc:
            self._error_text = (
                ErrorKind.MATH_ERR.value
                if str(exc).lower() == ErrorKind.MATH_ERR.value.lower()
                else ErrorKind.INVALID.value
            )
            print("Evalute token native error: ", exc)

    def _handle_equals(self) -> None:
        """Evaluate expression, update history and show result."""
        tokens = self._tokenize_expression()
        if not tokens:
            return

        value = self._evaluate_tokens(tokens, self._calculator)
        if value is None:
            self._force_error_display = True
            return None

        formatted_display = format_result(value)
        formatted_expr = clean_for_expression(formatted_display)

        expr = self._expression
        self._history.update_history(f"{expr}={formatted_expr}")
        self._expression = formatted_expr

        # Reset undo/redo navigation
        self._edit_ops.reset_navigation()

        self._just_solved = True

    def _handle_clear(self) -> None:
        self._expression = ""
        self._edit_ops.reset_navigation()
        self._just_solved = False

    def _handle_backspace(self) -> None:
        if self._expression:
            self._expression = self._expression[:-1]
        self._just_solved = False

    def _handle_negate(self) -> None:
        """Toggle sign of the last number in expression."""

        if self._expression in ("", Operation.SUB.symbol):
            self._expression = "" if self._expression else Operation.SUB.symbol
            return

        tokens = self._tokenize_expression()

        texts = [self._token_text(t) for t in tokens]

        for i in range(len(texts) - 1, -1, -1):
            txt = texts[i]

            if txt in self._operator_symbol_values:
                continue

            # Determine if previous text is unary minus attached to this token
            unary_prev = (
                i > 0
                and texts[i - 1] == Operation.SUB.symbol
                and (
                    i == 1
                    or texts[i - 2] in self._operator_symbol_values
                    or texts[i - 2] == Operation.OPEN_PAREN.symbol
                )
            )

            if unary_prev:
                texts.pop(i - 1)
            else:
                texts.insert(i, Operation.SUB.symbol)

            self._expression = "".join(str(t) for t in texts)
            return

    def _handle_memory(self, op: str) -> None:
        def current_value():
            tokens = self._tokenize_expression()
            if not tokens:
                return None

            return self._evaluate_tokens(tokens, self._calculator)

        def recall():
            if self._app_state.memory is None:
                return
            token = clean_for_expression(format_result(self._app_state.memory))
            if self._just_solved:
                self._expression = token
                self._just_solved = False
            else:
                self._expression += token

        def store(value):
            self._app_state.memory = value

        def add(value):
            self._app_state.memory = (
                value
                if self._app_state.memory is None
                else self._calculator.add(self._app_state.memory, value)
            )

        if op not in self._memory_ops:
            return

        def with_value(fn):
            value = current_value()
            if value is None:
                if self._error_text is not None:
                    self._force_error_display = True
                return
            fn(value)

        actions = {
            MemoryKey.MC.value: lambda: setattr(self._app_state, "memory", None),
            MemoryKey.MR.value: recall,
            MemoryKey.MS.value: lambda: with_value(store),
            MemoryKey.M_PLUS.value: lambda: with_value(add),
        }
        action = actions.get(op)
        if action is None:
            return
        action()
        self._topbar.set_memory_available(self._app_state.memory is not None)
        self._history.set_memory(
            "" if self._app_state.memory is None else format_result(self._app_state.memory)
        )

    def _build_handlers(self) -> Dict[Operation, Callable[[str], None]]:
        """Auto-generate operation handlers based on Operation attributes"""
        handlers: Dict[Operation, Callable[[str], None]] = {}

        # Special handlers
        special_handlers = {
            Operation.DIGIT: self._handle_digit,
            Operation.DOT: lambda _: self._handle_dot(),
            Operation.EQUALS: lambda _: self._handle_equals(),
            Operation.CLEAR: lambda _: self._handle_clear(),
            Operation.BACKSPACE: lambda _: self._handle_backspace(),
            Operation.NEGATE: lambda _: self._handle_negate(),
            Operation.HYP: lambda _: self._toggle_hyp(),
            Operation.IMAG: lambda _: self._handle_digit(Operation.IMAG.symbol),
        }
        handlers.update(special_handlers)

        def _make_set_operator_handler(operation: Operation) -> Callable[[str], None]:
            def _handler(label: str) -> None:
                self._set_operator(label, operation)

            return _handler

        # Auto-generate for operators (binary, postfix, parens)
        for op in Operation:
            if op in handlers:
                continue
            arity = getattr(op, "arity", None)
            if arity in ("binary", "postfix", "unary") or op in (
                Operation.OPEN_PAREN,
                Operation.CLOSE_PAREN,
            ):
                handlers[op] = _make_set_operator_handler(op)

        return handlers

    # Mode handlers
    def _toggle_hyp(self) -> None:
        self._app_state.hyp = not self._app_state.hyp

    def set_angle_unit(self, unit: AngleUnit) -> None:
        self._app_state.angle_unit = unit
        self._compute_and_update()

    # -- Helpers ----------------------------------------------------------

    def _tokenize_expression(self) -> List[object]:
        return self._tokenize_string(self._expression)

    def _token_text(self, tok: object) -> object:
        if tok.kind == calc_native.TokenKind.Number:
            return tok.value
        if tok.kind == calc_native.TokenKind.Op:
            if tok.op_id == calc_native.OpId.Negate:
                return Operation.SUB.symbol
            return tok.symbol
        if tok.kind == calc_native.TokenKind.LParen:
            return Operation.OPEN_PAREN.symbol
        if tok.kind == calc_native.TokenKind.RParen:
            return Operation.CLOSE_PAREN.symbol

    def _can_compute_preview(self, tokens: List[object]) -> bool:
        """Check if tokens form a valid expression for preview calculation."""
        if not tokens:
            return False

        if len(tokens) == 1:
            return is_number_token(tokens[0])

        last_text = self._token_text(tokens[-1])
        if not last_text:
            return False
        if last_text == Operation.OPEN_PAREN.symbol:
            return False
        if last_text in self._postfix_operator_symbols:
            return True
        if last_text in self._unary_operator_symbols:
            return False
        if last_text == Operation.CLOSE_PAREN.symbol:
            return True
        if last_text in self._operator_symbol_values:
            return False
        return True

    def _compute_preview(self, tokens: List[object], can_preview: bool) -> str:
        """Evaluate tokens and return formatted result"""

        if not can_preview:
            return ""

        value = self._evaluate_tokens(tokens, self._calculator)
        if value is None:
            return None

        formatted = format_result(value)
        self._result = formatted
        return formatted

    def _on_expression_input(self, text: str) -> None:
        """Handle keyboard input"""
        self._expression = text
        self._just_solved = False
        self._compute_and_update()

    def _show_and_clear_error(self) -> bool:
        if self._error_text is None:
            return False
        if self._force_error_display or not self._can_preview:
            self._display.update_res(self._error_text)  # forced action or invalid preview
        self._error_text = None
        self._force_error_display = False
        return True

    def _update_display(self) -> None:
        self._display.update_expr(self._expression)
        self._display.update_res(self._result)

    def _compute_and_update(self) -> None:
        """Recalculate preview and update display."""
        tokens = self._tokenize_expression()
        self._can_preview = self._can_compute_preview(tokens)
        self._result = self._compute_preview(tokens, self._can_preview)

        if not self._show_and_clear_error():
            self._update_display()
