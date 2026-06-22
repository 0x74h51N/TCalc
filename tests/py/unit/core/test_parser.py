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
from tcalc.core.varstore import VarStore, is_reserved

param = pytest.param


def build_rpn(op_ids, token_factory, rpn_spec):
    num, op, *_ = token_factory
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
    num, op, *_ = token_factory
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
    _num, op, *_ = token_factory
    rpn = [parser_mod.ValueOperand(5), op(op_ids.Negate)]
    assert parser_mod.evaluate_rpn(rpn, dummy_calc) == -5
    assert dummy_calc.calls == [("negate", (5,))]


# --- CharToken / assignment eval (fake tokens, no real calc_native) ---


@pytest.mark.parametrize(
    ("setup", "tokens_spec", "expected"),
    [
        param(
            {"A": 42},
            ("char", "A"),
            42,
            id="char-resolves-bound-variable",
        ),
        param(
            {},
            ("assign", "A", "num", 5),
            5,
            id="assignment-binds-and-returns",
        ),
    ],
)
def test_var_eval_cases(op_ids, token_factory, dummy_calc, setup, tokens_spec, expected):
    num, op, char = token_factory
    env = VarStore()
    for k, v in setup.items():
        env.set(k, v)
    it = iter(tokens_spec)
    tokens = []
    for kind in it:
        if kind == "char":
            tokens.append(char(next(it)))
        elif kind == "num":
            tokens.append(num(next(it)))
        elif kind == "assign":
            name = next(it)
            tokens.append(char(name))
            tokens.append(op(op_ids.Assign))
            next(it)  # "num"
            tokens.append(num(next(it)))
    if tokens_spec[0] == "assign":
        result = parser_mod.evaluate_tokens(tokens, dummy_calc, env)
        assert result == expected
        assert env.get(tokens_spec[1]) == expected
    else:
        assert parser_mod.evaluate_rpn(tokens, dummy_calc, env) == expected


@pytest.mark.parametrize(
    ("tokens_spec", "match"),
    [
        param(("char", "A"), "undefined variable A", id="char-undefined-variable"),
        param(("assign-reserved", "e", "num", 1), "reserved", id="assignment-reserved-name"),
        param(
            ("assign-non-char", "num", 2, "num", 5),
            "left of = must be a single letter",
            id="assignment-non-char-lhs",
        ),
        param(("assign-op-lhs", "Sub", "num", 2), "is an operator", id="assignment-op-lhs"),
        param(("rpn-assign",), "misplaced =", id="misplaced-assign-in-rpn"),
        param(("assign-empty", "A"), "no value", id="assignment-empty-rhs"),
    ],
)
def test_var_error_cases(op_ids, token_factory, dummy_calc, tokens_spec, match):
    num, op, char = token_factory
    kind = tokens_spec[0]
    if kind == "char":
        tokens = [char(tokens_spec[1])]
        with pytest.raises(errors.CalculatorError, match=match):
            parser_mod.evaluate_rpn(tokens, dummy_calc, VarStore())
    elif kind == "assign-reserved":
        name = tokens_spec[1]
        tokens = [char(name), op(op_ids.Assign), num(tokens_spec[3])]
        with pytest.raises(errors.CalculatorError, match=match):
            parser_mod.evaluate_tokens(tokens, dummy_calc, VarStore())
    elif kind == "assign-non-char":
        tokens = [num(tokens_spec[2]), op(op_ids.Assign), num(tokens_spec[4])]
        with pytest.raises(errors.CalculatorError, match=match):
            parser_mod.evaluate_tokens(tokens, dummy_calc, VarStore())
    elif kind == "assign-op-lhs":
        lhs_op_id = getattr(op_ids, tokens_spec[1])
        tokens = [op(lhs_op_id), op(op_ids.Assign), num(tokens_spec[3])]
        with pytest.raises(errors.CalculatorError, match=match):
            parser_mod.evaluate_tokens(tokens, dummy_calc, VarStore())
    elif kind == "rpn-assign":
        with pytest.raises(errors.CalculatorError, match=match):
            parser_mod.evaluate_rpn([op(op_ids.Assign)], dummy_calc)
    elif kind == "assign-empty":
        tokens = [char(tokens_spec[1]), op(op_ids.Assign)]
        with pytest.raises(errors.CalculatorError, match=match):
            parser_mod.evaluate_tokens(tokens, dummy_calc, VarStore())


# --- VarStore + is_reserved (moved here from a separate file) ---


@pytest.mark.parametrize(
    ("name", "reserved"),
    [
        param("e", True, id="constant"),
        param("sin", True, id="op-symbol"),
        param("add", True, id="op-alias"),
        param("A", False, id="plain-letter"),
        param("x", False, id="plain-letter-x"),
    ],
)
def test_is_reserved(name, reserved):
    assert is_reserved(name) is reserved


def test_varstore_set_get_clear():
    s = VarStore()
    assert s.get("A") is None
    s.set("A", 5)
    assert s.get("A") == 5
    s.set("A", 7)
    assert s.get("A") == 7
    s.clear()
    assert s.get("A") is None
