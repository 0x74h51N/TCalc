#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from unittest.mock import MagicMock

from tcalc.core.ops import Operation


def test_comma_operation_routes_to_handle_digit():
    """Operation.COMMA must invoke _handle_digit with ',' (mirrors DOT handler)."""
    from tcalc.ui.controller.controller import CalculatorController

    # Build a controller stub: bypass __init__; install the minimum attrs the
    # handler factory touches, then call _build_handlers.
    ctrl = CalculatorController.__new__(CalculatorController)
    ctrl._handle_digit = MagicMock()
    ctrl._display = MagicMock()
    ctrl._toggle_hyp = MagicMock()
    handlers = ctrl._build_handlers()

    handlers[getattr(Operation, "COMMA")]("any-label")
    ctrl._handle_digit.assert_called_once_with(",")


def _tokens(expr: str):
    import calc_native

    return list(calc_native.tokenize_string(expr).tokens)


def test_compute_status_empty_tokens_returns_blank():
    from tcalc.ui.controller.controller import _compute_status

    assert _compute_status([]) == ("", "")


def test_compute_status_unclosed_bracket_arity0():
    from tcalc.ui.controller.controller import _compute_status

    assert _compute_status(_tokens("[")) == ("none element list", "info")


def test_compute_status_unclosed_bracket_arity1():
    from tcalc.ui.controller.controller import _compute_status

    assert _compute_status(_tokens("[5")) == ("one element list", "info")


def test_compute_status_unclosed_bracket_arity2():
    from tcalc.ui.controller.controller import _compute_status

    assert _compute_status(_tokens("[1,2")) == ("two element list", "info")


def test_compute_status_unclosed_bracket_arity3():
    from tcalc.ui.controller.controller import _compute_status

    assert _compute_status(_tokens("[1,2,3")) == ("three element list", "info")


def test_compute_status_unclosed_bracket_arity_n_uses_digit():
    from tcalc.ui.controller.controller import _compute_status

    assert _compute_status(_tokens("[1,2,3,4,5")) == ("5 element list", "info")


def test_compute_status_closed_bracket_still_shows_info():
    from tcalc.ui.controller.controller import _compute_status

    # _compute_status now surfaces "N element list" for both closed and
    # unclosed brackets (info reflects current arity).
    assert _compute_status(_tokens("[1,2]")) == ("two element list", "info")


def test_compute_status_unclosed_paren_arity1_is_grouping_blank():
    from tcalc.ui.controller.controller import _compute_status

    # `(5` is plausible as grouping; do NOT label it as a 1-element point.
    assert _compute_status(_tokens("(5")) == ("", "")


def test_compute_status_unclosed_paren_arity2_is_point():
    from tcalc.ui.controller.controller import _compute_status

    assert _compute_status(_tokens("(1,2")) == ("two element point", "info")


def test_compute_status_multi_token_returns_blank():
    from tcalc.ui.controller.controller import _compute_status

    # `1+[2,3` -> tokens: [N(1), Op(+), ParenToken]; status suppressed.
    assert _compute_status(_tokens("1+[2,3")) == ("", "")


def test_compute_status_single_constant_shows_name():
    from tcalc.ui.controller.controller import _compute_status

    assert _compute_status(_tokens("c")) == ("Speed Of Light Constant", "info")
    assert _compute_status(_tokens("π")) == ("Pi Constant", "info")


def test_compute_status_subscript_constant_shows_name():
    from tcalc.ui.controller.controller import _compute_status

    assert _compute_status(_tokens("σ_{SB}")) == ("Stefan Boltzmann Constant", "info")


def test_compute_status_constant_with_more_tokens_blank():
    from tcalc.ui.controller.controller import _compute_status

    # Only a bare constant shows the name; anything else typed suppresses it.
    assert _compute_status(_tokens("c+2")) == ("", "")


def test_compute_status_subscript_variable_not_constant_blank():
    from tcalc.ui.controller.controller import _compute_status

    # x_{2} is a subscripted variable, not a constant -> no name.
    assert _compute_status(_tokens("x_{2}")) == ("", "")


def _make_stub_ctrl(expression: str, force: bool = False):
    import calc_native

    from tcalc.app_state import get_app_state
    from tcalc.ui.controller.controller import CalculatorController

    ctrl = CalculatorController.__new__(CalculatorController)
    ctrl._calculator = calc_native.Calculator()
    ctrl._app_state = get_app_state()
    ctrl._expression = expression
    ctrl._error_text = None
    ctrl._force_error_display = force
    ctrl._just_solved = False
    ctrl._result = None
    ctrl._display = MagicMock()
    # Default: result label starts empty (matches a fresh widget). Tests that
    # exercise "keep last result on live error" can override this before
    # calling _compute_and_update.
    ctrl._display.result.result_label.text.return_value = ""
    ctrl._history = MagicMock()
    ctrl._topbar = MagicMock()
    ctrl._memory_bar = MagicMock()
    return ctrl


def test_compute_and_update_live_eval_error_suppressed():
    """[[1,2]] live eval errors but status_kind != 'error' (suppressed)."""
    ctrl = _make_stub_ctrl("[[1,2]]")
    ctrl._compute_and_update()
    call = ctrl._display.result.update_res.call_args  # pyright: ignore[reportAttributeAccessIssue]
    assert call.kwargs.get("status_kind") != "error"
    assert call.args[0] == ""


def test_compute_and_update_force_display_surfaces_error():
    """Enter on [[1,2]] -> kind in result, reason detail in status."""
    ctrl = _make_stub_ctrl("[[1,2]]", force=True)
    ctrl._compute_and_update()
    call = ctrl._display.result.update_res.call_args  # pyright: ignore[reportAttributeAccessIssue]
    assert call.kwargs.get("status_kind") == "error"
    # Result shows the short kind; status surfaces the reason detail.
    assert call.kwargs.get("status_text") == "List of List not allowed"
    assert call.args[0] == "Invalid expression"


def test_compute_and_update_routes_info_status_for_unclosed_bracket():
    """[1,2,3 unclosed -> 'three element list' status, result format_result."""
    ctrl = _make_stub_ctrl("[1,2,3")
    ctrl._compute_and_update()
    call = ctrl._display.result.update_res.call_args  # pyright: ignore[reportAttributeAccessIssue]
    assert call.kwargs.get("status_kind") == "info"
    assert call.kwargs.get("status_text") == "three element list"
    # format_result uses native Collection repr (with closing char).
    assert call.args[0] == "[1, 2, 3]"


def test_compute_and_update_unclosed_bracket_inner_eval_live():
    """[2, 3+1 -> '[2, 4]' (inner eval via format_result)."""
    ctrl = _make_stub_ctrl("[2, 3+1")
    ctrl._compute_and_update()
    call = ctrl._display.result.update_res.call_args  # pyright: ignore[reportAttributeAccessIssue]
    assert call.args[0] == "[2, 4]"


def test_compute_and_update_unclosed_empty_bracket():
    """[ -> '[]' (eval returns empty list, format_result emits closed repr)."""
    ctrl = _make_stub_ctrl("[")
    ctrl._compute_and_update()
    call = ctrl._display.result.update_res.call_args  # pyright: ignore[reportAttributeAccessIssue]
    assert call.args[0] == "[]"


def test_compute_and_update_closed_bracket_full_format():
    """[2,3] closed -> '[2, 3]'."""
    ctrl = _make_stub_ctrl("[2,3]")
    ctrl._compute_and_update()
    call = ctrl._display.result.update_res.call_args  # pyright: ignore[reportAttributeAccessIssue]
    assert call.args[0] == "[2, 3]"


def test_compute_and_update_bare_comma_force_shows_short_status():
    """4,5 + Enter -> status_text short user-friendly; result_text 'Invalid inputs'."""
    ctrl = _make_stub_ctrl("4,5", force=True)
    ctrl._compute_and_update()
    call = ctrl._display.result.update_res.call_args  # pyright: ignore[reportAttributeAccessIssue]
    assert call.kwargs.get("status_kind") == "error"
    assert call.kwargs.get("status_text") == "Use [ ] for lists or ( ) for points"
    # result_text is the short 'Invalid inputs' label (not the long raw error).
    assert call.args[0] == "Invalid inputs"


def test_compute_and_update_bare_comma_live_suppressed():
    """4,5 live preview -> no error, no status (preview just blank)."""
    ctrl = _make_stub_ctrl("4,5")
    ctrl._compute_and_update()
    call = ctrl._display.result.update_res.call_args  # pyright: ignore[reportAttributeAccessIssue]
    assert call.kwargs.get("status_kind") != "error"
    assert call.args[0] == ""


def test_compute_and_update_unclosed_paren_grouping():
    """(5+3 -> '8' (arity-1 grouping scalar, format_result of int)."""
    ctrl = _make_stub_ctrl("(5+3")
    ctrl._compute_and_update()
    call = ctrl._display.result.update_res.call_args  # pyright: ignore[reportAttributeAccessIssue]
    assert call.args[0] == "8"


def test_short_error_suppressed_for_call_token():
    """A call's comma args are not bare commas: no list/point hint for gcd(...)."""
    from tcalc.ui.controller.controller import _short_error_for_expression

    expr = "gcd(21, 3/9)"
    assert _short_error_for_expression(expr, _tokens(expr)) is None


def test_short_error_fires_for_bare_comma():
    """Bare top-level comma (no enclosing paren/bracket/call) keeps the hint."""
    from tcalc.ui.controller.controller import _short_error_for_expression

    expr = "3,4"
    assert _short_error_for_expression(expr, _tokens(expr)) == "Use [ ] for lists or ( ) for points"


def test_handle_equals_feeds_grouping_free_expression():
    """Enter on a result >= 1000 must push a comma-free expression to the editor,
    so the next tokenize sees one Number (not comma-separated list elements)."""
    from tcalc.core.parser import tokenize

    ctrl = _make_stub_ctrl("1000000+234567")
    ctrl._tokenized = tokenize(ctrl._expression)
    ctrl.tokens = ctrl._tokenized.tokens
    ctrl._result = 1234567.0
    ctrl._edit_ops = MagicMock()

    ctrl._handle_equals()

    ctrl._display.editor.set_plain_text.assert_called_once_with("1234567")  # pyright: ignore[reportAttributeAccessIssue]
    assert ctrl._expression == "1234567"


def test_handle_equals_history_keeps_display_format():
    """History still records the human-readable display form (with separators)."""
    from tcalc.core.parser import tokenize

    ctrl = _make_stub_ctrl("1000000+234567")
    ctrl._tokenized = tokenize(ctrl._expression)
    ctrl.tokens = ctrl._tokenized.tokens
    ctrl._result = 1234567.0
    ctrl._edit_ops = MagicMock()

    ctrl._handle_equals()

    entry = ctrl._history.update_history.call_args.args[0]  # pyright: ignore[reportAttributeAccessIssue]
    assert entry.result == "1,234,567"


def _collection(items):
    import calc_native

    return calc_native.Collection(calc_native.Collection.Kind.List, items)


def test_memory_store_rejects_collection():
    """MS with a collection result must not enter memory; surfaces an error."""
    from tcalc.ui.widgets.calc.topbar.defins import MemoryKey

    ctrl = _make_stub_ctrl("[3,4,5]")
    ctrl._app_state.memory = None
    ctrl._result = _collection([3, 4, 5])

    ctrl._handle_memory(MemoryKey.MS.value)

    assert ctrl._app_state.memory is None
    call = ctrl._display.result.update_res.call_args
    assert call.kwargs.get("status_kind") == "error"
    assert call.kwargs.get("status_text") == "Memory holds numbers only"


def test_memory_add_rejects_collection_without_raising():
    """M+ with a collection result must not raise (add() crashed before)."""
    from tcalc.ui.widgets.calc.topbar.defins import MemoryKey

    ctrl = _make_stub_ctrl("[3,4,5,6]")
    ctrl._app_state.memory = None
    ctrl._result = _collection([3, 4, 5, 6])

    ctrl._handle_memory(MemoryKey.M_PLUS.value)  # must not raise

    assert ctrl._app_state.memory is None
    call = ctrl._display.result.update_res.call_args
    assert call.kwargs.get("status_kind") == "error"


def test_memory_store_accepts_scalar():
    """Regression guard: a normal scalar still stores."""
    from tcalc.ui.widgets.calc.topbar.defins import MemoryKey

    ctrl = _make_stub_ctrl("5")
    ctrl._app_state.memory = None
    ctrl._result = 5.0

    ctrl._handle_memory(MemoryKey.MS.value)

    assert ctrl._app_state.memory == 5.0


def _eval_error(expr: str):
    """Run _evaluate_tokens on a bare controller stub; return (kind, detail)."""
    import calc_native

    from tcalc.core.parser import tokenize
    from tcalc.ui.controller.controller import CalculatorController

    ctrl = CalculatorController.__new__(CalculatorController)
    ctrl._evaluate_tokens(tokenize(expr), calc_native.Calculator(), calc_native.AngleUnit.DEG)
    return ctrl._error_text, ctrl._error_detail


def test_math_error_detail_surfaces():
    assert _eval_error("gcd(21,3/9)") == ("Math Error", "gcd is only defined for integers")


def test_invalid_detail_surfaces():
    assert _eval_error("sin(90,3)") == ("Invalid expression", "sin takes 1 argument")


def test_malformed_detail_stays_hidden():
    kind, detail = _eval_error("1++")
    assert kind == "Malformed Expression"
    assert detail is None
