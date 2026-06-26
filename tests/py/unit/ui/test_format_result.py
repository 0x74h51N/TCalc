#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import calc_native

from tcalc.core.parser import tokenize
from tcalc.ui.controller.utils import format_result


def _list(items):
    return calc_native.Collection(calc_native.Collection.Kind.List, items)


def _point(items):
    return calc_native.Collection(calc_native.Collection.Kind.Point, items)


def test_format_result_list_of_ints():
    assert format_result(_list([1, 2, 3])) == "[1, 2, 3]"


def test_format_result_point():
    assert format_result(_point([1, 2])) == "(1, 2)"


def test_format_result_list_of_points():
    assert format_result(_list([_point([1, 2]), _point([3, 4])])) == "[(1, 2), (3, 4)]"


def test_format_result_empty_list():
    assert format_result(_list([])) == "[]"


# -- group flag: display grouping vs tokenizer-safe default ----------------


def _single_token(expr: str):
    toks = list(tokenize(expr).tokens)
    assert len(toks) == 1, f"{expr!r} -> {[t.kind for t in toks]}"
    return toks[0]


def test_default_omits_grouping_commas():
    assert format_result(1234567.89) == "1234567.89"
    assert format_result(1234567.0) == "1234567"


def test_group_true_adds_thousands_separators():
    assert format_result(1234567.89, group=True) == "1,234,567.89"
    assert format_result(1234567.0, group=True) == "1,234,567"


def test_default_scalar_round_trips_to_single_number():
    # The grouped form "1,234,567.89" splits into 5 tokens; the default form
    # must tokenize back to a single Number.
    tok = _single_token(format_result(1234567.89))
    assert tok.kind == calc_native.TokenKind.Number


def test_collection_commas_survive_and_round_trip():
    # Element-separator commas are valid list syntax (no grouping applied).
    assert format_result(_list([1000000, 2, 3])) == "[1000000, 2, 3]"
    tok = _single_token(format_result(_list([1000000, 2, 3])))
    assert tok.kind == calc_native.TokenKind.Paren


def test_default_complex_round_trips():
    assert format_result(3 + 4j) == "3+4i"
