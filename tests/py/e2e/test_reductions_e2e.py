#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import pytest

pytest.importorskip("calc_native")
import calc_native

param = pytest.param


def _eval(expr: str) -> object:
    from tcalc.core.engine import Calculator
    from tcalc.core.parser import evaluate_tokens, tokenize_string

    calc = Calculator()
    return evaluate_tokens(tokenize_string(expr), calc)


@pytest.mark.parametrize(
    ("expr", "expected_type", "expected_value"),
    [
        # ----------------------------
        # mean — scalar arms
        # ----------------------------
        param("mean[1,2,3,4]", "float", 2.5, id="mean-int-even-to-double"),
        param("mean[1,2,3]", "float", 2.0, id="mean-int-odd-to-double"),
        param("mean[1.5, 2.5]", "float", 2.0, id="mean-double"),
        # ----------------------------
        # unary-op auto-inserts "(": the arg paren must be transparent grouping,
        # so "mean([..])" == "mean[..]" (the inner List passes through unchanged).
        # ----------------------------
        param("mean([1,2,3,4,5,6])", "float", 3.5, id="mean-paren-wrapped-list"),
        param("min([3,1,2])", "float", 1.0, id="min-paren-wrapped-list"),
        param("median([1,2,3,4])", "float", 2.5, id="median-paren-wrapped-list"),
        param("mean[1e400, 3e400]", "BigReal", "e+400", id="mean-bigreal-arm"),
        param("mean[1+2j, 3+4j]", "complex", (2.0, 3.0), id="mean-complex-arm"),
        # ----------------------------
        # mean — List of Points → centroid
        # ----------------------------
        param("mean[(0,0),(2,4)]", "Point", (1.0, 2.0), id="mean-centroid"),
        # ----------------------------
        # mean — result chains into other ops (plain CalcValue)
        # ----------------------------
        param("mean[1,2,3]+10", "float", 12.0, id="mean-chains-add"),
        param("2*mean[2,4,6]", "float", 8.0, id="mean-chains-mul"),
        param("sqrt(mean[16,16])", "float", 4.0, id="mean-chains-into-sqrt"),
        # ----------------------------
        # min / max — keep the input arm, single scan
        # ----------------------------
        param("min[3,1,2]", "float", 1.0, id="min-int"),
        param("max[3,1,2]", "float", 3.0, id="max-int"),
        param("min[1.5, 0.5, 2.5]", "float", 0.5, id="min-double"),
        # ----------------------------
        # median — nth_element; odd keeps arm, even averages
        # ----------------------------
        param("median[5,1,4,2,3]", "float", 3.0, id="median-odd-shuffled"),
        param("median[1,2,3,4]", "float", 2.5, id="median-even-averages"),
        # ----------------------------
        # min / max — List of Points → bounding-box corners
        # ----------------------------
        param("min[(1,4),(3,2)]", "Point", (1.0, 2.0), id="min-bbox-low-corner"),
        param("max[(1,4),(3,2)]", "Point", (3.0, 4.0), id="max-bbox-high-corner"),
    ],
)
def test_reduction_eval_golden(expr: str, expected_type: str, expected_value: object) -> None:
    out = _eval(expr)

    if expected_type == "float":
        assert isinstance(out, (int, float))
        assert float(out) == pytest.approx(expected_value)
        return

    if expected_type == "complex":
        assert isinstance(out, complex)
        assert isinstance(expected_value, tuple)
        assert out.real == pytest.approx(expected_value[0])
        assert out.imag == pytest.approx(expected_value[1])
        return

    if expected_type == "Point":
        assert isinstance(out, calc_native.Collection)
        assert out.kind == calc_native.Collection.Kind.Point
        assert isinstance(expected_value, tuple)
        assert len(out) == len(expected_value)
        for actual, expected in zip(out, expected_value):
            assert actual == pytest.approx(expected)
        return

    # BigReal (and any stringly-checked arm): substring match on repr.
    assert type(out).__name__ == expected_type
    assert isinstance(expected_value, str)
    assert expected_value in str(out)


@pytest.mark.parametrize(
    ("expr", "expected_msg_substr"),
    [
        param("mean[]", "mean of an empty collection", id="mean-empty"),
        param("min[]", "min of an empty collection", id="min-empty"),
        param("mean(3,4)", "mean is not defined for a single point", id="mean-bare-point"),
        param("median(3,4)", "median is not defined for a single point", id="median-bare-point"),
        param("min[1+2j, 3]", "min-max not defined for complex values", id="min-complex"),
        param("max[1+2j, 3]", "min-max not defined for complex values", id="max-complex"),
        param("median[1+2j, 3]", "median is not defined for complex values", id="median-complex"),
    ],
)
def test_reduction_eval_errors(expr: str, expected_msg_substr: str) -> None:
    from tcalc.errors import Error

    with pytest.raises(Error) as exc_info:
        _eval(expr)
    assert expected_msg_substr in str(exc_info.value)
