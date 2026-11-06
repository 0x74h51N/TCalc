#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from types import ModuleType


class FakeArity(Enum):
    Unary = "unary"
    Binary = "binary"
    Postfix = "postfix"


class Id(Enum):
    Add = "add"
    Sub = "sub"
    Div = "div"
    Negate = "negate"
    Percent = "percent"
    Sin = "sin"
    Pow = "pow"
    Root = "root"
    Assign = "assign"


@dataclass(frozen=True)
class _OpDef:
    id: Id
    symbol: str
    arity: FakeArity
    method: str
    aliases: tuple[str, ...] = ()


class FakeBigReal:
    pass


class FakeBigComplex:
    pass


class FakeRational:
    pass


class FakeCollection:
    pass


_FAKE_OPS: tuple[_OpDef, ...] = (
    _OpDef(
        Id.Add,
        "+",
        FakeArity.Binary,
        Id.Add.value,
        aliases=("add",),
    ),
    _OpDef(Id.Sub, "-", FakeArity.Binary, Id.Sub.value),
    _OpDef(Id.Div, "/", FakeArity.Binary, Id.Div.value),
    _OpDef(Id.Negate, "u-", FakeArity.Unary, Id.Negate.value),
    _OpDef(Id.Percent, "%", FakeArity.Postfix, Id.Percent.value),
    _OpDef(Id.Sin, "sin", FakeArity.Unary, Id.Sin.value),
    _OpDef(
        Id.Pow,
        "^",
        FakeArity.Binary,
        Id.Pow.value,
    ),
    _OpDef(Id.Root, "⌄", FakeArity.Binary, Id.Root.value),
    _OpDef(Id.Assign, "=", FakeArity.Binary, Id.Assign.value),
)


class ExprKind(Enum):
    Frac = "frac"
    Pow = "pow"
    Root = "root"


@dataclass(frozen=True)
class LatexExprEntry:
    symbol: str
    kind: ExprKind
    opid: Id


def latex_exprs():
    return [
        LatexExprEntry("\\frac", ExprKind.Frac, Id.Div),
        LatexExprEntry("^", ExprKind.Pow, Id.Pow),
        LatexExprEntry("\\sqrt", ExprKind.Root, Id.Root),
    ]


def _install_fake_calc_native() -> ModuleType:
    calc_native = ModuleType("calc_native")

    def op_table():
        return list(_FAKE_OPS)

    calc_native.op_table = op_table

    class FakeConstId(Enum):
        Pi = 0
        EulerNumber = 1
        Imaginary = 2

    calc_native.ConstId = FakeConstId

    class _ConstDef:
        def __init__(self, cid, symbol, aliases, value):
            self.id, self.symbol, self.aliases, self.value = cid, symbol, aliases, value

    _FAKE_CONSTS = [
        _ConstDef(FakeConstId.Pi, "π", ["pi"], 3.141592653589793),
        _ConstDef(FakeConstId.EulerNumber, "e", [], 2.718281828459045),
        _ConstDef(FakeConstId.Imaginary, "i", ["I", "j", "J"], complex(0, 1)),
    ]
    calc_native.const_table = lambda: list(_FAKE_CONSTS)

    calc_native.BigReal = FakeBigReal
    calc_native.BigComplex = FakeBigComplex
    calc_native.Rational = FakeRational
    calc_native.Collection = FakeCollection
    calc_native.latex_exprs = latex_exprs
    return calc_native


# Ensure core modules can be imported without the real native extension.
sys.modules["calc_native"] = _install_fake_calc_native()


_CANONICAL_CONFTST = "tests.py.unit.core.conftest"
if __name__ != _CANONICAL_CONFTST:
    sys.modules.setdefault(_CANONICAL_CONFTST, sys.modules[__name__])
