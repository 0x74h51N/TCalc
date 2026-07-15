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
from types import ModuleType
from typing import Callable, List, Optional


@dataclass(frozen=True)
class FakeToken:
    kind: object
    value: Optional[object] = None
    op_id: Optional[object] = None
    left: Optional[List["FakeToken"]] = None
    right: Optional[List["FakeToken"]] = None
    expr_kind: Optional[object] = None
    const_id: object = None

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

    def as_char(self) -> Optional["FakeToken"]:
        return self if self.kind == FakeTokenKind.Char else None

    def as_const(self) -> Optional["FakeToken"]:
        return self if self.kind == FakeTokenKind.Const else None

    @property
    def id(self):
        return self.const_id


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
    Assign = "assign"
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
    call_arity: int = 1
    cx: Callable[..., bool] | None = None

    @property
    def angle_unit(self) -> bool:
        """Alias for needs_angle_unit to match native OpSpec property name."""
        return self.needs_angle_unit

    @property
    def is_variadic(self) -> bool:
        """Match native OpSpec: call_arity == kVariadicArity (0xFF)."""
        return self.call_arity == 0xFF

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


class FakeParenKind(Enum):
    Paren = 0
    Brace = 1
    Bracket = 2


class FakeTokenKind:
    Number = "number"
    Op = "op"
    Latex = "latex"
    Paren = "paren"
    Call = "call"
    Char = "char"
    Const = "const"


class FakeCollectionKind:
    List = "list"
    Point = "point"


@dataclass(frozen=True)
class FakeCollection:
    kind: object
    items: tuple

    def __post_init__(self):
        if self.kind == FakeCollectionKind.Point:
            if len(self.items) == 0:
                raise ValueError("empty Point not supported")
            if len(self.items) >= 4:
                raise ValueError("Point arity > 3 not supported")
            for it in self.items:
                if isinstance(it, FakeCollection):
                    raise ValueError("Point cannot contain Collection items")
        else:
            if not self.items:
                return
            has_col = any(isinstance(it, FakeCollection) for it in self.items)
            if not has_col:
                return
            all_col = all(isinstance(it, FakeCollection) for it in self.items)
            if not all_col:
                raise ValueError("List elements must all be scalars OR all be Points")
            first_arity = None
            for it in self.items:
                if it.kind != FakeCollectionKind.Point:
                    raise ValueError("nested List not allowed")
                if first_arity is None:
                    first_arity = len(it.items)
                elif len(it.items) != first_arity:
                    raise ValueError("list-of-points must have uniform arity")

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, i):
        return self.items[i]


def _cx_sqrt(x: float) -> bool:
    return x < 0.0


def _cx_root(x: float, y: float) -> bool:
    return x < 0.0


def _cx_log(x: float) -> bool:
    return x <= 0.0


_FAKE_OPS: tuple[_OpDef, ...] = (
    _OpDef(
        Id.Add,
        "+",
        FakeArity.Binary,
        Id.Add.value,
        aliases=("add",),
        big_supported=True,
        big_complex_supported=True,
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
    _OpDef(Id.Assign, "=", FakeArity.Binary, Id.Assign.value),
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

    calc_native.ParenKind = FakeParenKind

    calc_native.OpId = Id

    calc_native.OpSpec = _OpDef

    def op_table():
        return [op for op in _FAKE_OPS if op.symbol]

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
    calc_native.ConstSpec = _ConstDef
    calc_native.const_table = lambda: list(_FAKE_CONSTS)

    def _unavailable(*_args, **_kwargs):
        raise NotImplementedError("calc_native is faked in unit tests")

    calc_native.tokenize_string = _unavailable
    calc_native.shunting_yard = list

    calc_native.BigReal = FakeBigReal
    calc_native.BigComplex = FakeBigComplex
    calc_native.Rational = FakeRational
    # Collection.Kind is exposed as an inner attribute (matching native binding).
    FakeCollection.Kind = FakeCollectionKind
    calc_native.Collection = FakeCollection
    calc_native.Calculator = DummyCalc
    calc_native.CalculatorError = FakeNativeCalculatorError
    calc_native.Token = FakeToken

    calc_native.ExprKind = ExprKind

    calc_native.latex_exprs = latex_exprs
    calc_native.LatexExprEntry = LatexExprEntry
    return calc_native


# Ensure core modules can be imported without the real native extension.
sys.modules["calc_native"] = _install_fake_calc_native()


_CANONICAL_CONFTST = "tests.py.unit.core.conftest"
if __name__ != _CANONICAL_CONFTST:
    sys.modules.setdefault(_CANONICAL_CONFTST, sys.modules[__name__])
