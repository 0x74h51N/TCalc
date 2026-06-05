#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import calc_native
import pytest

from tcalc.core.engine import Calculator
from tcalc.core.parser import evaluate_tokens, tokenize_string
from tcalc.errors import Error


def _eval(expr: str):
    return evaluate_tokens(tokenize_string(expr), Calculator())


def _list(items):
    return calc_native.Collection(calc_native.Collection.Kind.List, items)


def _point(items):
    return calc_native.Collection(calc_native.Collection.Kind.Point, items)


def test_eval_bare_number_list():
    assert _eval("[1, 2, 3]") == _list([1, 2, 3])


def test_eval_list_arity_1_demote():
    assert _eval("[5]") == 5


def test_eval_list_arity_1_demote_with_expr():
    # arity-1 demote returns the inner expr result; integer arithmetic stays Rational.
    out = _eval("[2+3]")
    assert isinstance(out, calc_native.Rational)
    assert (out.numerator, out.denominator) == (5, 1)


def test_eval_point_arity_1_demote_grouping():
    out = _eval("(1+2)*3")
    assert isinstance(out, calc_native.Rational)
    assert (out.numerator, out.denominator) == (9, 1)


def test_eval_empty_list():
    assert _eval("[]") == _list([])


def test_eval_empty_point_error():
    with pytest.raises(Error):
        _eval("()")


def test_eval_point_arity_2():
    assert _eval("(3, 4)") == _point([3, 4])


def test_eval_point_arity_3():
    assert _eval("(1, 2, 3)") == _point([1, 2, 3])


def test_eval_point_arity_4_error():
    with pytest.raises(Error):
        _eval("(1, 2, 3, 4)")


def test_eval_list_with_latex_element():
    assert _eval("[\\frac{1}{2}, 3]") == _list([0.5, 3.0])


def test_eval_list_with_expression_element():
    assert _eval("[1+2, 3*4]") == _list([3, 12])


# Hot-eval continues to work while the user is typing — an unclosed paren of
# any kind keeps producing a value (grouping result, Collection, etc.).


def test_eval_unclosed_paren_grouping():
    # "(2+3" still evaluates as 5; missing close does not block eval.
    out = _eval("(2+3")
    assert isinstance(out, calc_native.Rational)
    assert (out.numerator, out.denominator) == (5, 1)


def test_eval_unclosed_bracket_list():
    # "[1,2,3" still builds a 3-element List.
    assert _eval("[1,2,3") == _list([1, 2, 3])


def test_eval_unclosed_brace_grouping():
    # "{2+3" — Brace is grouping; arity-1 still evaluates.
    out = _eval("{2+3")
    assert isinstance(out, calc_native.Rational)
    assert (out.numerator, out.denominator) == (5, 1)


def test_eval_stray_close_skipped():
    # Stray ')' in mid-expression is a no-op orphan from segment editing;
    # the surrounding expression still evaluates.
    out = _eval("1+2)")
    assert isinstance(out, calc_native.Rational)
    assert (out.numerator, out.denominator) == (3, 1)


def test_eval_nested_list_error():
    with pytest.raises(Error):
        _eval("[[1,2], 3]")


def test_eval_list_of_points_ok():
    # nested Collection == Collection currently compares structurally via repr
    # (variant element equality doesn't recurse into Collection items yet).
    expected = _list([_point([1, 2]), _point([3, 4])])
    result = _eval("[(1,2), (3,4)]")
    assert isinstance(result, calc_native.Collection)
    assert result.kind == calc_native.Collection.Kind.List
    assert len(result) == 2
    assert result[0] == _point([1, 2])
    assert result[1] == _point([3, 4])
    assert repr(result) == repr(expected)


def test_eval_list_of_points_mixed_arity_error():
    with pytest.raises(Error):
        _eval("[(1,2), (3,4,5)]")


def test_eval_list_mixed_scalar_point_error():
    with pytest.raises(Error):
        _eval("[1, (2,3)]")


def test_eval_point_of_point_error():
    with pytest.raises(Error):
        _eval("((1,2), (3,4))")


def test_eval_nested_arity_1_demote_chain():
    assert _eval("[[5]]") == 5


def test_eval_scalar_plus_collection_error():
    # binary `add(scalar, Collection)` undefined; wrapped as Error.
    with pytest.raises(Error):
        _eval("5 + [1, 2]")


def test_eval_empty_element_in_list_error():
    with pytest.raises(Error):
        _eval("[1, ]")
