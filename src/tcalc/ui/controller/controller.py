#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional, Sequence

import calc_native

from tcalc.app_state import AngleUnit, get_app_state
from tcalc.core.ops import Operation
from tcalc.core.utils import is_number_token
from tcalc.ui.controller.menubar import EditOperations
from tcalc.ui.widgets import History
from tcalc.ui.widgets.calc import Display, TopBar

from ...core import Calculator, evaluate_tokens, tokenize_string
from ..widgets.calc.topbar.defins import MEMORY_KEYS, MemoryKey
from .utils import apply_hyp_variant, clean_for_expression, format_result

_log = logging.getLogger("tcalc.ui.controller")


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

        self._expression = self._display.editor.get_plain_text()

        self.tokens: List[calc_native.Token] = []
        self._result: Optional[object] = None
        self._just_solved = False
        self._error_text: Optional[str] = None
        self._force_error_display = False

        self._memory_ops = {str(k["operation"]) for k in MEMORY_KEYS}

        # Build handlers dictionary
        self._handlers: Dict[Operation, Callable[[str], None]] = self._build_handlers()

        self._tokenize_string = tokenize_string
        self._history.set_memory("")
        self._compute_and_update()

    def handle_key(self, label: str, operation) -> None:
        self._just_solved = False

        if operation == "shift":
            self._app_state.shifted = not self._app_state.shifted
            return

        if isinstance(operation, str) and operation in self._memory_ops:
            self._handle_memory(operation)

        elif isinstance(operation, Operation):
            # Hyp variant
            operation = apply_hyp_variant(operation, self._app_state.hyp)
            label = operation.symbol
            handler = self._handlers.get(operation)
            assert handler is not None
            handler(label)
        else:
            self._handle_digit(label)

    # -- Handlers ---------------------------------------------------------

    def _handle_digit(self, label: str) -> None:
        self._display.editor.apply_key(label, Operation.DIGIT)

    def _handle_equals(self) -> None:
        """Evaluate expression, update history and show result."""
        if not self.tokens:
            return

        if self._result is None:
            self._force_error_display = True
            self._compute_and_update()
            return

        formatted_res = clean_for_expression(format_result(self._result))
        expr = self._expression
        self._history.update_history(f"{expr}={formatted_res}")
        self._just_solved = True
        self._display.editor.set_plain_text(formatted_res)
        self._expression = formatted_res

        self._edit_ops.reset_navigation()

    def _handle_clear(self) -> None:
        self._display.editor.set_plain_text("")
        self._expression = ""
        self._edit_ops.reset_navigation()

    def _handle_memory(self, op: str) -> None:
        def recall() -> None:
            if self._app_state.memory is None:
                return
            token = clean_for_expression(format_result(self._app_state.memory))
            self._display.editor.insert_text(token)

        def store(value) -> None:
            self._app_state.memory = value

        def add(value) -> None:
            self._app_state.memory = (
                value
                if self._app_state.memory is None
                else self._calculator.add(self._app_state.memory, value)
            )

        def with_value(fn) -> None:
            value = self._result
            if value is None:
                self._force_error_display = True
                self._compute_and_update()
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
        handlers.update(
            {
                Operation.DIGIT: self._handle_digit,
                Operation.DOT: lambda _: self._handle_digit(Operation.DOT.symbol),
                Operation.EQUALS: lambda _: self._handle_equals(),
                Operation.CLEAR: lambda _: self._handle_clear(),
                Operation.BACKSPACE: lambda _: self._display.editor.backspace(),
                Operation.NEGATE: lambda _: self._display.editor.handle_negate(),
                Operation.HYP: lambda _: self._toggle_hyp(),
                Operation.IMAG: lambda _: self._handle_digit(Operation.IMAG.symbol),
                Operation.DIV: lambda _: self._display.editor.insert_expr_str(
                    calc_native.ExprKind.Frac
                ),
                Operation.POW: lambda _: self._display.editor.insert_expr_str(
                    calc_native.ExprKind.Pow
                ),
                Operation.ROOT: lambda _: self._display.editor.insert_expr_str(
                    calc_native.ExprKind.Root
                ),
            }
        )

        def _make_set_operator_handler(operation: Operation) -> Callable[[str], None]:
            def _handler(_label: str) -> None:
                self._display.editor.apply_key(operation.symbol, operation)

            return _handler

        # Auto-generate for operators (binary, postfix, parens)
        for op in Operation:
            if op in handlers:
                continue
            handlers[op] = _make_set_operator_handler(op)

        return handlers

    # -- Helpers ----------------------------------------------------------

    def _evaluate_tokens(self, tokens: Sequence[calc_native.Token], calculator: Calculator):
        try:
            return evaluate_tokens(tokens, calculator)
        except Exception as exc:
            self._error_text = str(exc)
            _log.debug("Evaluate token native error: %s", exc)

    def _can_compute_preview(self, tokens: List[calc_native.Token]) -> bool:
        if not tokens:
            return False
        if len(tokens) == 1 and tokens[0].kind != calc_native.TokenKind.Expr:
            return is_number_token(tokens[0])

        return True

    def _on_expression_input(self, text: str) -> None:
        # Keyboard typing
        self._expression = text
        self._compute_and_update()

    def _compute_and_update(self) -> None:
        self.tokens = self._tokenize_string(self._expression)
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
