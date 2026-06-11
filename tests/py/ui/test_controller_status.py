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


def _make_stub_ctrl(expression: str, force: bool = False):
    from tcalc.app_state import get_app_state
    from tcalc.core.engine import Calculator
    from tcalc.ui.controller.controller import CalculatorController

    ctrl = CalculatorController.__new__(CalculatorController)
    ctrl._calculator = Calculator()
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
    """Enter on [[1,2]] -> short error visible in both status and result."""
    ctrl = _make_stub_ctrl("[[1,2]]", force=True)
    ctrl._compute_and_update()
    call = ctrl._display.result.update_res.call_args  # pyright: ignore[reportAttributeAccessIssue]
    assert call.kwargs.get("status_kind") == "error"
    # Short form: only ErrorKind.value (no embedded detail).
    assert call.kwargs.get("status_text") == "Invalid expression"
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
