#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from enum import Enum
from types import ModuleType, SimpleNamespace
from typing import Callable, List, Optional

import pytest


@dataclass(frozen=True)
class FakeToken:
    kind: object
    value: Optional[object] = None
    op_id: Optional[object] = None
    left: Optional[List["FakeToken"]] = None
    right: Optional[List["FakeToken"]] = None
    expr_kind: Optional[object] = None

    @property
    def data(self):
        if self.kind == FakeTokenKind.Number:
            return type("Data", (), {"value": self.value})()
        if self.kind == FakeTokenKind.Op:
            return type("Data", (), {"op_id": self.op_id})()
        return None

    def as_number(self) -> Optional["FakeToken"]:
        return self if self.kind == FakeTokenKind.Number else None

    def as_op(self) -> Optional["FakeToken"]:
        return self if self.kind == FakeTokenKind.Op else None


class FakeArity(Enum):
    Unary = "unary"
    Binary = "binary"
    Postfix = "postfix"

    @property
    def name(self) -> str:
        return self._name_


class Id(Enum):
    Add = "add"
    Sub = "sub"
    Div = "div"
    Negate = "negate"
    Percent = "percent"
    Sin = "sin"
    Pow = "pow"
    Sqrt = "sqrt"
    Log = "log"
    Ln = "ln"
    Asin = "asin"
    Acos = "acos"
    Acosh = "acosh"
    Atanh = "atanh"
    Root = "root"
    BAD_TYPE = "bad_type"
    BAD_NATIVE = "bad_native"
    CEKOMASTIK = "cekomastik"

    @property
    def _spec(self) -> _OpDef:
        return _FAKE_OP_BY_ID[self]

    @property
    def cx(self) -> Callable[..., bool] | None:
        """Complex promotion rule from fake op table."""
        return _FAKE_OP_BY_ID[self].cx

    @property
    def big_supported(self) -> bool:
        return _FAKE_OP_BY_ID[self].big_supported

    @property
    def bigcomplex_supported(self) -> bool:
        return _FAKE_OP_BY_ID[self].big_complex_supported


@dataclass(frozen=True)
class _OpDef:
    # Use same field names as native OpSpec - no property mapping needed!
    id: Id
    symbol: str
    arity: FakeArity
    method: str
    precedence: int = 0
    associativity: int = 0
    aliases: tuple[str, ...] = ()
    needs_angle_unit: bool = False
    big_supported: bool = False
    big_complex_supported: bool = False
    cx: Callable[..., bool] | None = None

    @property
    def angle_unit(self) -> bool:
        """Alias for needs_angle_unit to match native OpSpec property name."""
        return self.needs_angle_unit

    def __iter__(self):
        return iter(
            (
                self.id,
                self.symbol,
                self.precedence,
                self.associativity,
                self.arity,
                self.aliases,
                self.method,
                self.needs_angle_unit,
                self.big_supported,
                self.big_complex_supported,
            )
        )


class DummyCalc:
    def __init__(self):
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def add(self, a, b):
        self.calls.append((Id.Add.value, (a, b)))
        return a + b

    def sub(self, a, b):
        self.calls.append((Id.Sub.value, (a, b)))
        return a - b

    def div(self, a, b):
        self.calls.append((Id.Div.value, (a, b)))
        return a / b

    def negate(self, a):
        self.calls.append((Id.Negate.value, (a,)))
        return -a

    def percent(self, a):
        self.calls.append((Id.Percent.value, (a,)))
        return a / 100

    def sin(self, a, unit):
        self.calls.append((Id.Sin.value, (a, unit)))
        return (a, unit)

    def pow(self, a, b):
        self.calls.append((Id.Pow.value, (a, b)))
        return pow(a, b)

    def sqrt(self, a):
        self.calls.append((Id.Sqrt.value, (a,)))
        return a

    def bad_type(self, *args):
        raise TypeError("bad-type")

    def bad_native(self, *args):
        raise FakeNativeCalculatorError("bad-native")


class FakeBigReal:
    def __init__(self, value: str):
        self.value = str(value)

    def __str__(self) -> str:
        return self.value


class FakeBigRealFail:
    def __init__(self, value: str):
        raise ValueError(f"bad BigReal: {value}")


class FakeBigComplex:
    def __init__(self, *parts: str):
        self.parts = parts

    def __str__(self) -> str:
        return f"FakeBigComplex({', '.join(self.parts)})"


class FakeNativeCalculatorError(Exception):
    pass


class FakeRational(float):
    def __new__(cls, *args):
        if len(args) == 2:
            value = args[0] / args[1]
        elif len(args) == 1:
            value = args[0]
        else:
            value = 0
        return super().__new__(cls, value)


class FakeParenType(Enum):
    Open = 0
    Close = 1


class FakeParenKind(Enum):
    Paren = 0
    Brace = 1
    Bracket = 2


_FAKE_PAREN_TABLE: list[tuple[str, FakeParenType, FakeParenKind]] = [
    ("(", FakeParenType.Open, FakeParenKind.Paren),
    (")", FakeParenType.Close, FakeParenKind.Paren),
]


class FakeTokenKind:
    Number = "number"
    Op = "op"
    Expr = "expr"
    Paren = "paren"


def _cx_sqrt(x: float) -> bool:
    return x < 0.0


def _cx_root(x: float, y: float) -> bool:
    return x < 0.0


def _cx_log(x: float) -> bool:
    return x <= 0.0


_FAKE_OPS: tuple[_OpDef, ...] = (
    _OpDef(
        Id.Add, "+", FakeArity.Binary, Id.Add.value, big_supported=True, big_complex_supported=True
    ),
    _OpDef(Id.Sub, "-", FakeArity.Binary, Id.Sub.value),
    _OpDef(Id.Div, "/", FakeArity.Binary, Id.Div.value),
    _OpDef(Id.Negate, "u-", FakeArity.Unary, Id.Negate.value),
    _OpDef(Id.Percent, "%", FakeArity.Postfix, Id.Percent.value),
    _OpDef(Id.Sin, "sin", FakeArity.Unary, Id.Sin.value, needs_angle_unit=True),
    _OpDef(
        Id.Pow,
        "^",
        FakeArity.Binary,
        Id.Pow.value,
        cx=_cx_root,
        big_supported=True,
        big_complex_supported=True,
    ),
    _OpDef(
        Id.Sqrt,
        "sqrt",
        FakeArity.Unary,
        Id.Sqrt.value,
        cx=_cx_sqrt,
        big_supported=True,
        big_complex_supported=True,
    ),
    _OpDef(Id.Root, "⌄", FakeArity.Binary, Id.Root.value, cx=_cx_root),
    _OpDef(Id.Log, "log", FakeArity.Unary, Id.Log.value, cx=_cx_log),
    _OpDef(Id.Ln, "ln", FakeArity.Unary, Id.Ln.value, cx=_cx_log),
    _OpDef(Id.Asin, "asin", FakeArity.Unary, Id.Asin.value),
    _OpDef(Id.Acos, "acos", FakeArity.Unary, Id.Acos.value),
    _OpDef(Id.Acosh, "acosh", FakeArity.Unary, Id.Acosh.value),
    _OpDef(Id.Atanh, "atanh", FakeArity.Unary, Id.Atanh.value),
    _OpDef(Id.BAD_TYPE, "", FakeArity.Binary, Id.BAD_TYPE.value),
    _OpDef(Id.BAD_NATIVE, "", FakeArity.Binary, Id.BAD_NATIVE.value),
)

_FAKE_OP_BY_ID: dict[Id, _OpDef] = {op.id: op for op in _FAKE_OPS}


class ExprKind(Enum):
    Frac = "frac"
    Pow = "pow"
    Root = "root"
    Log = "log"


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
        LatexExprEntry("\\log", ExprKind.Log, Id.Log),
    ]


def _install_fake_calc_native() -> ModuleType:
    calc_native = ModuleType("calc_native")

    calc_native.e = math.e
    calc_native.pi = math.pi
    calc_native.i = 1j

    class AngleUnit(Enum):
        DEG = "DEG"
        RAD = "RAD"

    calc_native.AngleUnit = AngleUnit

    calc_native.TokenKind = FakeTokenKind

    calc_native.OpArity = FakeArity

    calc_native.ParenType = FakeParenType
    calc_native.ParenKind = FakeParenKind
    calc_native.paren_table = lambda: list(_FAKE_PAREN_TABLE)

    calc_native.OpId = Id

    calc_native.OpSpec = _OpDef

    def op_table():
        return [op for op in _FAKE_OPS if op.symbol]

    calc_native.op_table = op_table

    def _unavailable(*_args, **_kwargs):
        raise NotImplementedError("calc_native is faked in unit tests")

    calc_native.tokenize_string = _unavailable
    calc_native.shunting_yard = _unavailable

    calc_native.BigReal = FakeBigReal
    calc_native.BigComplex = FakeBigComplex
    calc_native.Rational = FakeRational
    calc_native.Calculator = DummyCalc
    calc_native.CalculatorError = FakeNativeCalculatorError
    calc_native.Token = FakeToken

    calc_native.ExprKind = ExprKind

    calc_native.latex_exprs = latex_exprs
    calc_native.LatexExprEntry = LatexExprEntry
    return calc_native


# Ensure core modules can be imported without the real native extension.
sys.modules["calc_native"] = _install_fake_calc_native()


@pytest.fixture
def dummy_calc() -> DummyCalc:
    return DummyCalc()


@pytest.fixture
def token_factory():
    def num(value):
        return FakeToken(FakeTokenKind.Number, value=value)

    def op(op_id):
        return FakeToken(FakeTokenKind.Op, op_id=op_id)

    return num, op


@pytest.fixture
def fake_ops(monkeypatch) -> dict[Id, _OpDef]:
    from tcalc.core import parser as parser_mod

    ops = _FAKE_OP_BY_ID

    monkeypatch.setattr(parser_mod, "OP_BY_ID", ops)
    monkeypatch.setattr(
        parser_mod, "calc_native", SimpleNamespace(TokenKind=FakeTokenKind), raising=False
    )
    monkeypatch.setattr(
        parser_mod, "is_number_token", lambda tok: tok.token.kind == FakeTokenKind.Number
    )
    return ops


@pytest.fixture
def op_ids() -> type[Id]:
    return Id


@pytest.fixture
def angle_unit(monkeypatch) -> str:
    from tcalc import app_state

    monkeypatch.setattr(app_state, "get_app_state", lambda: SimpleNamespace(angle_unit="DEG"))
    return "DEG"


@pytest.fixture
def fake_parse_number(monkeypatch):
    from tcalc.core import parser as parser_mod

    def parse(value: str) -> int | float:
        if "." not in value and "e" not in value.lower():
            return int(value)
        return float(value)

    monkeypatch.setattr(parser_mod, "parse_number_token", parse)
    monkeypatch.setattr(
        parser_mod, "calc_native", SimpleNamespace(Rational=FakeRational), raising=False
    )


@pytest.fixture
def fake_calc_native(monkeypatch):
    from tcalc.core import utils as utils_mod

    monkeypatch.setattr(
        utils_mod,
        "calc_native",
        SimpleNamespace(BigReal=FakeBigReal, Rational=FakeRational),
        raising=False,
    )


@pytest.fixture
def fake_engine(monkeypatch):
    from tcalc.core import engine as engine_mod

    monkeypatch.setattr(engine_mod, "Operation", Id)
    return engine_mod


_CANONICAL_CONFTST = "tests.py.unit.core.conftest"
if __name__ != _CANONICAL_CONFTST:
    sys.modules.setdefault(_CANONICAL_CONFTST, sys.modules[__name__])
