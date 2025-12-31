from __future__ import annotations

import pytest

from tcalc.core import errors
from tcalc.core import parser as parser_mod


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


def test_rpn_operand_check_malformed_raises(fake_ops, op_ids, token_factory, dummy_calc):
    _, op = token_factory
    tokens = [op(op_ids.PERCENT)]

    with pytest.raises(errors.Error):
        parser_mod.evaluate_rpn(tokens, dummy_calc)


def test_rpn_malformed_unary_raises(fake_ops, op_ids, token_factory, dummy_calc):
    _, op = token_factory
    tokens = [op(op_ids.NEGATE)]

    with pytest.raises(errors.Error):
        parser_mod.evaluate_rpn(tokens, dummy_calc)


def test_rpn_malformed_binary_raises(fake_ops, op_ids, token_factory, dummy_calc):
    num, op = token_factory
    tokens = [num(69), op(op_ids.ADD)]

    with pytest.raises(errors.Error):
        parser_mod.evaluate_rpn(tokens, dummy_calc)


def test_coerce_token_constant():
    assert parser_mod._coerce_token("π") == parser_mod.CONSTANTS["π"]


def test_coerce_token_number(fake_parse_number):
    assert parser_mod._coerce_token("123") == 123

def test_coerce_token_invalid_raises(fake_parse_number):
    with pytest.raises(errors.Error):
        parser_mod._coerce_token("si")
