from __future__ import annotations

import pytest

from tcalc.core import errors
from tcalc.core import parser as parser_mod

param = pytest.param


def test_rpn_binary_order(fake_ops, op_ids, token_factory, dummy_calc):
    num, op = token_factory
    tokens = [num(41), num(69), op(op_ids.SUB)]

    assert parser_mod.evaluate_rpn(tokens, dummy_calc) == -28


def test_rpn_unary_and_postfix(fake_ops, op_ids, token_factory, dummy_calc):
    num, op = token_factory
    tokens = [num(50), op(op_ids.PERCENT), op(op_ids.NEGATE)]

    assert parser_mod.evaluate_rpn(tokens, dummy_calc) == -0.5


def test_rpn_needs_unit(fake_ops, op_ids, token_factory, dummy_calc, angle_unit):
    num, op = token_factory
    tokens = [num(1), op(op_ids.SIN)]

    assert parser_mod.evaluate_rpn(tokens, dummy_calc) == (1, angle_unit)


@pytest.mark.parametrize(
    "rpn",
    [
        param(("op", "PERCENT"), id="postfix-missing-operand"),
        param(("op", "NEGATE"), id="unary-missing-operand"),
        param(("num", 69, "op", "ADD"), id="binary-missing-operand"),
    ],
)
def test_rpn_malformed_raises(fake_ops, op_ids, token_factory, dummy_calc, rpn):
    num, op = token_factory
    it = iter(rpn)
    tokens = []
    for kind in it:
        if kind == "num":
            tokens.append(num(next(it)))
        elif kind == "op":
            tokens.append(op(getattr(op_ids, next(it))))
        else:
            raise AssertionError(f"Unknown rpn kind: {kind!r}")

    with pytest.raises(errors.Error):
        parser_mod.evaluate_rpn(tokens, dummy_calc)


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        param("π", parser_mod.CONSTANTS["π"], id="constant-pi"),
        param("123", 123, id="number-int"),
    ],
)
def test_coerce_token(literal, expected, fake_parse_number):
    assert parser_mod._coerce_token(literal) == expected


def test_coerce_token_invalid_raises(fake_parse_number):
    with pytest.raises(errors.Error):
        parser_mod._coerce_token("si")
