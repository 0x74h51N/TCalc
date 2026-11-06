#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from tcalc.core import ops as ops_mod
from tests.py.unit.core.conftest import FakeArity
from tests.py.unit.core.conftest import Id


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


def test_comma_operation_exists_and_has_correct_symbol():
    comma = getattr(ops_mod.Operation, "COMMA")
    assert comma.symbol == ","
    # COMMA is a UI-only op (no native OpId), so arity must be None.
    assert comma.arity is None
