from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ...app_state import AngleUnit, get_app_state

from ...core import  Operation, CalculatorError, get_symbols_with_aliases, evaluate_tokens, tokenize_string
from ...core.utils import is_number_token
from .utils import format_result, clean_for_expression


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
        
        # Build handlers dictionary
        self._handlers: Dict[Operation, Callable[[str], None]] = self._build_handlers()

        # Get all operator symbols including aliases
        self._operator_symbol_values = get_symbols_with_aliases(
            lambda op: getattr(op, "symbol", None) is not None
        )
        
        # Get unary operator symbols
        self._unary_operator_symbols = get_symbols_with_aliases(
            lambda op: getattr(op, "arity", None) == "unary"
        )

        # Get postfix operator symbols
        self._postfix_operator_symbols = get_symbols_with_aliases(
            lambda op: getattr(op, "arity", None) == "postfix"
        )

        self._evaluate_tokens = evaluate_tokens
        self._tokenize_string = tokenize_string

        self._history.set_memory("")
        self._compute_and_update()

    def handle_key(self, label: str, operation) -> None:
        """Dispatch button press to appropriate handler."""
        
        if operation == "shift":
            self._app_state.shifted = not self._app_state.shifted
            self._compute_and_update()
            return
        
        if isinstance(operation, str) and operation in {"MC", "MR", "MS", "M+", "M-"}:
            self._handle_memory(operation)
            self._compute_and_update()
            return
        
        if not isinstance(operation, Operation):
            self._handle_digit(label)
            self._compute_and_update()
            return

        if self._app_state.hyp and operation in (Operation.SIN, Operation.COS, Operation.TAN):
            operation = {
                Operation.SIN: Operation.SINH,
                Operation.COS: Operation.COSH,
                Operation.TAN: Operation.TANH,
            }[operation]
            label = operation.symbol

        handler = self._handlers.get(operation)
        if handler is None:
            print(f"[CONTROLLER] Handler not found: {operation} (label: {label})")
            return
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

    def _set_operator(self, label: str) -> None:
        self._expression += label
        self._just_solved = False

    def _handle_equals(self) -> None:
        """Evaluate expression, update history and show result."""
        tokens = self._tokenize_expression()
        if not tokens or not self._can_compute_preview(tokens):
            return
        
        try:
            value = self._evaluate_tokens(tokens, self._calculator)
        except CalculatorError as exc:
            self._error_text = str(exc)
            return
        
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
        self._just_solved = False

    def _handle_backspace(self) -> None:
        if self._expression:
            self._expression = self._expression[:-1]
        self._just_solved = False

    def _handle_negate(self) -> None:
        """Toggle sign of the last number in expression."""
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
        self._expression = Operation.SUB.symbol + self._expression if Operation.SUB.symbol not in self._expression else ""

    def _handle_memory(self, op: str) -> None:
        def current_value():
            tokens = self._tokenize_expression()
            if not tokens or not self._can_compute_preview(tokens):
                return None
            try:
                return self._evaluate_tokens(tokens, self._calculator)
            except CalculatorError:
                return None

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
            if value is None:
                return
            self._app_state.memory = value

        def add(value):
            if value is None:
                return
            self._app_state.memory = value if self._app_state.memory is None else self._calculator.add(self._app_state.memory, value)

        def sub(value):
            if value is None:
                return
            self._app_state.memory = value if self._app_state.memory is None else self._calculator.sub(self._app_state.memory, value)

        actions = {
            "MC": lambda: setattr(self._app_state, "memory", None),
            "MR": recall,
            "MS": lambda: store(current_value()),
            "M+": lambda: add(current_value()),
            "M-": lambda: sub(current_value()),
        }
        actions[op]()
        self._topbar.set_memory_available(self._app_state.memory is not None)
        self._history.set_memory("" if self._app_state.memory is None else format_result(self._app_state.memory))

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
        }
        handlers.update(special_handlers)
        
        # Auto-generate for operators (binary, postfix, parens)
        for op in Operation:
            if op in handlers:
                continue
            arity = getattr(op, "arity", None)
            if arity in ("binary", "postfix", "unary") or op in (Operation.OPEN_PAREN, Operation.CLOSE_PAREN):
                handlers[op] = self._set_operator
        
        return handlers

    def _toggle_hyp(self) -> None:
        self._app_state.hyp = not self._app_state.hyp

    # Mode handlers
    def set_angle_unit(self, unit: AngleUnit) -> None:
        self._app_state.angle_unit = unit
        self._compute_and_update()


    # -- Helpers ----------------------------------------------------------

    def _tokenize_expression(self) -> List[str]:
        return self._tokenize_string(self._expression)

    def _can_compute_preview(self, tokens: List[str]) -> bool:
        """Check if tokens form a valid expression for preview calculation."""
        if len(tokens) < 2:
            return False

        # Prevent preview if last token is unary op and next is open paren (e.g. sqrt()
        if len(tokens) >= 2 and tokens[-2] in self._unary_operator_symbols  and tokens[-1] == Operation.OPEN_PAREN.symbol:
            return False

        # Unary/postfix + number handling: only allow preview if one is a number and the other is unary/postfix
        if len(tokens) == 2:
            t0, t1 = tokens[0], tokens[1]
            is_t0_unary = t0 in self._unary_operator_symbols
            is_t1_unary = t1 in self._unary_operator_symbols
            is_t0_postfix = t0 in self._postfix_operator_symbols
            is_t1_postfix = t1 in self._postfix_operator_symbols
            is_t0_number = is_number_token(t0)
            is_t1_number = is_number_token(t1)

            # Disallow cases like '√-' (unary + minus)
            if (is_t0_unary and t1 == Operation.SUB.symbol) or (is_t1_unary and t0 == Operation.SUB.symbol):
                return False
            # Allow only if one is number and the other is unary or postfix
            if (is_t0_number and (is_t1_unary or is_t1_postfix)) or ((is_t0_unary or is_t0_postfix) and is_t1_number):
                return True
            return False

        # If last token is operator and has res, show res
        last_is_operator = tokens[-1] in self._operator_symbol_values and tokens[-1] != Operation.PERCENT.symbol
        if last_is_operator:
            return self._result != ""

        # Check last token is valid
        return tokens[-1] not in self._operator_symbol_values or tokens[-1] == Operation.PERCENT.symbol

    def _compute_preview(self, tokens: List[str]) -> str:
        """Evaluate tokens and return formatted result"""

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
        """Handle keyboard input"""
        self._expression = text
        self._just_solved = False
        self._compute_and_update()

    def _compute_and_update(self) -> None:
        """Recalculate preview and update display."""
        if self._error_text is not None:
            self._display.update_res(self._error_text)
            self._error_text = None
            return

        tokens = self._tokenize_expression()
        self._result = self._compute_preview(tokens)
        
        self._display.update_expr(self._expression)
        self._display.update_res(self._result)
