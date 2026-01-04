from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional

import calc_native

from tcalc.app_state import AngleUnit, get_app_state
from tcalc.core import Calculator, evaluate_tokens, tokenize_string
from tcalc.core.ops import Operation, get_symbols_with_aliases
from tcalc.core.utils import is_number_token
from tcalc.ui.controller.menubar import EditOperations
from tcalc.ui.widgets import History
from tcalc.ui.widgets.calc import Display, TopBar

from ..widgets.calc.topbar.defins import MEMORY_KEYS, MemoryKey
from .utils import clean_for_expression, format_result


class CalculatorController:
    """Main controller handling calculator input, expression state and display updates."""

    def __init__(
        self,
        calculator: Calculator,
        display: Display,
        history: History,
        edit_ops: EditOperations,
        topbar: TopBar,
    ) -> None:
        self._calculator: Calculator = calculator
        self._display: Display = display
        self._history: History = history
        self._edit_ops: EditOperations = edit_ops
        self._topbar: TopBar = topbar
        self._app_state = get_app_state()

        self._display.expression_changed.connect(self._on_expression_input)

        self._expression: str = ""
        self.tokens: List[object] = []
        self._result: Optional[object] = None
        self._just_solved = False
        self._error_text: Optional[str] = None
        self._force_error_display = False

        self._memory_ops = {str(k["operation"]) for k in MEMORY_KEYS}

        # Build handlers dictionary
        self._handlers: Dict[Operation, Callable[[str], None]] = self._build_handlers()

        # Get all operator symbols including aliases
        self._operator_symbol_values = get_symbols_with_aliases()
        self._operator_symbol_values.discard(Operation.IMAG.symbol)

        # Get binary operator symbols
        self._binary_operator_symbols = get_symbols_with_aliases(
            lambda spec: spec.arity == "binary"
        )

        self._tokenize_string = tokenize_string
        self._history.set_memory("")
        self._compute_and_update()

    def handle_key(self, label: str, operation) -> None:
        """Dispatch button press to appropriate handler."""
        self._just_solved = False
        if operation == "shift":
            self._app_state.shifted = not self._app_state.shifted
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

        self._expression += label

    def _handle_dot(self) -> None:
        self._expression += Operation.DOT.symbol

    def _handle_equals(self) -> None:
        """Evaluate expression, update history and show result."""
        if not self.tokens:
            return

        if self._result is None:
            self._force_error_display = True
            return

        formatted_res = clean_for_expression(format_result(self._result))
        expr = self._expression
        self._history.update_history(f"{expr}={formatted_res}")
        self._expression = formatted_res
        self._just_solved = True

        # Reset undo/redo navigation
        self._edit_ops.reset_navigation()

    def _handle_clear(self) -> None:
        self._expression = ""
        self._edit_ops.reset_navigation()

    def _handle_backspace(self) -> None:
        if self._expression:
            self._expression = self._expression[:-1]

    def _handle_negate(self) -> None:
        """Toggle sign of the last number in expression."""

        if self._expression in ("", Operation.SUB.symbol):
            self._expression = "" if self._expression else Operation.SUB.symbol
            return

        texts = [self._token_text(t) for t in self.tokens]

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
        def recall():
            if self._app_state.memory is None:
                return
            token = clean_for_expression(format_result(self._app_state.memory))

            self._expression += token

        def store(value):
            self._app_state.memory = value

        def add(value):
            self._app_state.memory = (
                value
                if self._app_state.memory is None
                else self._calculator.add(self._app_state.memory, value)
            )

        def with_value(fn):
            value = self._result
            if value is None:
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

    # Mode handlers
    def _toggle_hyp(self) -> None:
        self._app_state.hyp = not self._app_state.hyp

    def set_angle_unit(self, unit: AngleUnit) -> None:
        self._app_state.angle_unit = unit
        self._compute_and_update()

    # -- Handle factory ------------------------------------------------------

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

    # -- Helpers ----------------------------------------------------------

    def _set_operator(self, _label: str, operation: Operation) -> None:
        symbol = operation.symbol
        arity = getattr(operation, "arity", None)
        if arity == "unary":
            self._expression += f"{symbol}{Operation.OPEN_PAREN.symbol}"
        elif arity == "binary":
            self._expression += f" {symbol} "
        else:
            self._expression += symbol

    def _evaluate_tokens(self, tokens: Iterable[object], calculator: Calculator):
        """Call core.evaluate_tokens; on CalculatorError log and return the error text."""
        try:
            return evaluate_tokens(tokens, calculator)
        except Exception as exc:
            self._error_text = str(exc)
            print("Evalute token native error: ", exc)

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
        if last_text == Operation.OPEN_PAREN.symbol:
            return False
        return True

    def _on_expression_input(self, text: str) -> None:
        """Handle keyboard input"""
        self._expression = text
        self._compute_and_update()

    def _compute_and_update(self) -> None:
        """Recalculate preview and update display."""

        self.tokens = self._tokenize_string(self._expression)
        self._display.update_expr(self._expression)
        _can_preview = self._can_compute_preview(self.tokens)

        result_text = ""
        if self._force_error_display or _can_preview:
            self._result = self._evaluate_tokens(self.tokens, self._calculator)

        if self._result is None:
            if self._force_error_display and self._error_text:
                result_text = self._error_text
        else:
            self._error_text = None
            if _can_preview and not self._just_solved:
                result_text = format_result(self._result)

        self._force_error_display = False
        self._display.update_res(result_text)
