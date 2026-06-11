#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import calc_native

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
