#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest

from tcalc.core import ops as ops_mod
from tests.py.unit.core.conftest import FakeArity, Id

param = pytest.param


def test_ops_tables_are_built_from_fakes():
    assert ops_mod.OP_BY_ID

    for op_id, spec in ops_mod.OP_BY_ID.items():
        assert isinstance(op_id, Id)
        assert isinstance(spec.symbol, str)
        assert isinstance(spec.arity, FakeArity)

        op = getattr(ops_mod.Operation, op_id.name.upper())
        assert op._spec is spec
        assert op.symbol == spec.symbol


def test_ui_ops():
    assert ops_mod.Operation.DIGIT.symbol == "digit"
    assert ops_mod.Operation.OPEN_PAREN.symbol == "("
    assert ops_mod.Operation.CLOSE_PAREN.symbol == ")"
    assert ops_mod.Operation.EQUALS.symbol == "="


def test_symbols_with_aliases():
    symbols = ops_mod.get_symbols_with_aliases()
    assert symbols

    for op in ops_mod.Operation:
        spec = op._spec
        if spec.symbol:
            assert spec.symbol in symbols
        for alias in spec.aliases:
            assert alias in symbols


def test_promo_rules_wired():
    """Verify PROMO_RULES_BY_ID is correctly wired."""
    for op_id in ops_mod.PROMO_RULES_BY_ID:
        assert op_id in ops_mod.OP_BY_ID, f"PROMO_RULES_BY_ID has {op_id} but OP_BY_ID doesn't"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        param(3.0, True, id="int"),
        param(2.0000000000001, True, id="epsilon-close"),
        param(2.1, False, id="fractional"),
    ],
)
def test_is_int_like(value, expected):
    assert ops_mod.is_int_like(value) is expected


@pytest.mark.parametrize(
    ("x", "y", "promotes"),
    [
        param(8.0, 2.0, False, id="pos-base"),
        param(-8.0, 3.0, False, id="neg-odd-int"),
        param(-8.0, 2.0, True, id="neg-even-int"),
        param(-8.0, 2.5, True, id="neg-non-int"),
    ],
)
def test_root_rule(x, y, promotes):
    assert ops_mod._cx_root(x, y) is promotes
