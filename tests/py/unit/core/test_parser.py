#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest

from tcalc import errors
from tcalc.core import parser as parser_mod

param = pytest.param


def build_rpn(op_ids, token_factory, rpn_spec):
    num, op = token_factory
    it = iter(rpn_spec)
    tokens = []
    for kind in it:
        if kind == "num":
            value = next(it)
            tokens.append(num(value).as_number())
        elif kind == "op":
            op_id = next(it)
            tokens.append(op(getattr(op_ids, op_id)).as_op())
        else:
            raise AssertionError(f"Unknown rpn kind: {kind!r}")
    return tokens


@pytest.mark.parametrize(
    ("rpn_spec", "expected"),
    [
        param(("num", 41, "num", 69, "op", "Sub"), -28, id="binary-order-sub"),
        param(("num", 50, "op", "Percent", "op", "Negate"), -0.5, id="postfix-then-unary"),
        param(("num", 6, "num", 2, "op", "Div"), 3, id="binary-order-div"),
        param(("num", 2, "num", 8, "op", "Pow"), 256, id="binary-pow-basic"),
        param(("num", 5, "op", "Negate", "op", "Negate"), 5, id="unary-chain-negate-negate"),
        param(
            ("num", 50, "op", "Percent", "op", "Percent"), 0.005, id="postfix-chain-percent-percent"
        ),
    ],
)
def test_evaluate_rpn_cases(op_ids, token_factory, dummy_calc, rpn_spec, expected):
    tokens = build_rpn(op_ids, token_factory, rpn_spec)
    assert parser_mod.evaluate_rpn(tokens, dummy_calc) == expected


def test_rpn_needs_unit(op_ids, token_factory, dummy_calc, angle_unit):
    num, op = token_factory
    tokens = [num(1), op(op_ids.Sin)]
    assert parser_mod.evaluate_rpn(tokens, dummy_calc) == (1, angle_unit)


@pytest.mark.parametrize(
    "rpn_spec",
    [
        param(("op", "Percent"), id="postfix-missing-operand"),
        param(("op", "Negate"), id="unary-missing-operand"),
        param(("num", 69, "op", "Add"), id="binary-missing-operand"),
        param(("num", 123, "op", "Add"), id="binary-missing-second-operand"),
    ],
)
def test_rpn_malformed_raises(op_ids, token_factory, dummy_calc, rpn_spec):
    tokens = build_rpn(op_ids, token_factory, rpn_spec)
    with pytest.raises(errors.Error):
        parser_mod.evaluate_rpn(tokens, dummy_calc)


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        param("π", parser_mod.CONSTANTS["π"], id="constant-pi"),
        param("123", 123, id="number-int"),
    ],
)
def test_coerce_token(literal, expected):
    assert parser_mod._coerce_token(literal) == expected


def test_coerce_token_invalid_raises():
    with pytest.raises(errors.Error):
        parser_mod._coerce_token("si")


def test_value_operand_pushed_directly(dummy_calc):
    sentinel = object()
    rpn = [parser_mod.ValueOperand(sentinel)]
    assert parser_mod.evaluate_rpn(rpn, dummy_calc) is sentinel


def test_value_operand_feeds_into_op(op_ids, token_factory, dummy_calc):
    _num, op = token_factory
    rpn = [parser_mod.ValueOperand(5), op(op_ids.Negate)]
    assert parser_mod.evaluate_rpn(rpn, dummy_calc) == -5
    assert dummy_calc.calls == [("negate", (5,))]
