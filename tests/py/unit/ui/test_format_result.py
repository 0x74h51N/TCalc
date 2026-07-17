#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import calc_native
import pytest

from tcalc.core.native_eval import evaluate_branch
from tcalc.core.parser import tokenize
from tcalc.ui.controller.utils import format_result


def _eval(expr: str):
    return evaluate_branch(tokenize(expr), calc_native.Calculator(), calc_native.AngleUnit.RAD)


def _frag(x) -> str:
    # A Collection's repr is valid expression syntax ("(1, 2)" / "[1, 2]").
    return repr(x) if isinstance(x, calc_native.Collection) else str(x)


def _list(items):
    return _eval("[" + ",".join(_frag(x) for x in items) + "]")


def _point(items):
    return _eval("(" + ",".join(_frag(x) for x in items) + ")")


# -- value -> string -------------------------------------------------------
#
# group=False is the tokenizer-safe default (no thousands separators) so the
# output can be fed back into the editor; group=True is for display widgets.

FORMAT_CASES = [
    pytest.param(_list([1, 2, 3]), False, "[1, 2, 3]", id="list-of-ints"),
    pytest.param(_point([1, 2]), False, "(1, 2)", id="point"),
    pytest.param(
        _list([_point([1, 2]), _point([3, 4])]), False, "[(1, 2), (3, 4)]", id="list-of-points"
    ),
    pytest.param(_list([]), False, "[]", id="empty-list"),
    # Element separators are list syntax, so they survive the no-grouping default.
    pytest.param(_list([1000000, 2, 3]), False, "[1000000, 2, 3]", id="collection-keeps-commas"),
    pytest.param(1234567.89, False, "1234567.89", id="float-plain"),
    pytest.param(1234567.0, False, "1234567", id="float-integral-plain"),
    pytest.param(1234567.89, True, "1,234,567.89", id="float-grouped"),
    pytest.param(1234567.0, True, "1,234,567", id="float-integral-grouped"),
    pytest.param(3 + 4j, False, "3+4i", id="complex"),
    # An exact value must not be shown through a double: float() holds neither an
    # int64 nor an integer Rational past 2**53.
    pytest.param(_eval("10^{16}+1"), False, "1.0000000000000001e+16", id="exact-int-past-double"),
    pytest.param(
        _eval("9223372036854775807"), False, "9.223372036854775807e+18", id="int64-max-literal"
    ),
    pytest.param(_eval("2+3"), False, "5", id="exact-int-small"),
    pytest.param(_eval("10^{6}+1"), True, "1,000,001", id="exact-int-grouped"),
    pytest.param(_eval("\\frac{1}{4}"), False, "0.25", id="exact-fraction-decimal"),
]


@pytest.mark.parametrize("value,group,expected", FORMAT_CASES)
def test_format_result(value, group, expected):
    assert format_result(value, group=group) == expected


# -- output parses back to one token ---------------------------------------

ROUND_TRIP_CASES = [
    pytest.param(1234567.89, calc_native.TokenKind.Number, id="float"),
    pytest.param(_eval("10^{16}+1"), calc_native.TokenKind.Number, id="exact-int-past-double"),
    pytest.param(_list([1000000, 2, 3]), calc_native.TokenKind.Paren, id="collection"),
]


@pytest.mark.parametrize("value,expected_kind", ROUND_TRIP_CASES)
def test_default_output_round_trips(value, expected_kind):
    # The grouped form "1,234,567.89" would split into 5 tokens; the default form
    # must come back as one.
    text = format_result(value)
    toks = list(tokenize(text).tokens)
    assert len(toks) == 1, f"{text!r} -> {[t.kind for t in toks]}"
    assert toks[0].kind == expected_kind
