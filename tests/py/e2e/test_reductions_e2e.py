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


def test_value_operand_feeds_prebuilt_collection_into_mean() -> None:
    from tcalc.core.engine import Calculator
    from tcalc.core.parser import (
        ValueOperand,
        evaluate_rpn,
        shunting_yard,
        tokenize_string,
    )

    calc = Calculator()

    # A pre-built runtime Collection (as if produced earlier / stored).
    collection = evaluate_rpn(shunting_yard(tokenize_string("[1,2,3,4]")), calc)
    assert isinstance(collection, calc_native.Collection)

    # The real mean OpToken, taken from a normal tokenized reduction.
    mean_op = shunting_yard(tokenize_string("mean[1,2,3]"))[1]
    assert mean_op.kind == calc_native.TokenKind.Op
    assert mean_op.as_op().op_id == calc_native.OpId.Mean

    # Inject the pre-built collection straight into eval; no list re-tokenize.
    result = evaluate_rpn([ValueOperand(collection), mean_op], calc)
    assert isinstance(result, (int, float))
    assert float(result) == pytest.approx(2.5)


def test_call_token_evaluates_function():
    from tcalc.core.engine import Calculator
    from tcalc.core.parser import evaluate_tokens, tokenize_string

    calc = Calculator()
    out = evaluate_tokens(tokenize_string("sin(45)"), calc)  # DEG default
    assert isinstance(out, (int, float))
    a = evaluate_tokens(tokenize_string("mean([1,2,3])"), calc)
    b = evaluate_tokens(tokenize_string("mean[1,2,3]"), calc)
    assert isinstance(a, (int, float)) and isinstance(b, (int, float))
    assert float(a) == pytest.approx(float(b)) == pytest.approx(2.0)


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        param("x̄(2,3,5,6)", 4.0, id="mean-bare-args"),
        param("x̄[2,3,5,6]", 4.0, id="mean-bracket"),
        param("x̄([2,3,5,6])", 4.0, id="mean-paren-wrapped-list"),
        param("x̄(2,3)", 2.5, id="mean-two-args"),
        param("gcd(12,8)", 4, id="gcd-two-args"),
        param("gcd(12,8,6)", 2, id="gcd-three-args"),
        param("gcd[12,8]", 4, id="gcd-bracket"),
        param("gcd([12,8])", 4, id="gcd-paren-wrapped-list"),
        param("lcm(4,6)", 12, id="lcm-two-args"),
    ],
)
def test_variadic_call_args(expr: str, expected: float) -> None:
    result = _eval(expr)
    assert isinstance(result, (int, float))
    assert result == float(expected)


@pytest.mark.parametrize(
    ("expr", "expected_msg_substr"),
    [
        param("x̄((3,4))", "single point", id="mean-of-point"),
        param("sin(45,2)", "takes 1 argument", id="too-many-args"),
        param("sin([2,3])", "not defined for a list or point", id="scalar-fn-collection"),
        param("gcd(21, 3/9)", "only defined for integers", id="gcd-non-integer"),
        param("lcm(4, 2.5)", "only defined for integers", id="lcm-non-integer"),
    ],
)
def test_call_arg_errors(expr: str, expected_msg_substr: str) -> None:
    from tcalc.errors import Error

    with pytest.raises(Error) as exc_info:
        _eval(expr)
    assert expected_msg_substr in str(exc_info.value)
