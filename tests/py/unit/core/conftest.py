from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import ModuleType, SimpleNamespace
from typing import Callable
import math
import pytest

import sys


@dataclass(frozen=True)
class FakeToken:
    kind: object
    op_id: object | None = None
    value: object | None = None


class FakeOpId(Enum):
    ADD = "add"
    SUB = "sub"
    NEGATE = "negate"
    PERCENT = "percent"
    SIN = "sin"
    POW = "pow"
    SQRT = "sqrt"
    LOG = "log"
    LN = "ln"
    ASIN = "asin"
    ACOS = "acos"
    ACOSH = "acosh"
    ATANH = "atanh"
    ROOT = "root"

    BAD_TYPE = "bad_type"
    BAD_NATIVE = "bad_native"
    CEKOMASTIK = "cekomastik"

    @property
    def spec(self) -> FakeSpec:
        return _FAKE_OP_SPECS[self]

    @property
    def big_supported(self) -> bool:
        return _FAKE_OP_SPECS[self].big

    @property
    def bigcomplex_supported(self) -> bool:
        return _FAKE_OP_SPECS[self].bigcx


@dataclass(frozen=True)
class FakeSpec:
    arity: str
    method: str
    needs_unit: bool = False
    sym: str = ""
    cx: Callable[..., bool] | None = None
    big: bool = False
    bigcx: bool = False


class DummyCalc:
    def __init__(self):
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def add(self, a, b):
        self.calls.append(("add", (a, b)))
        return a + b

    def sub(self, a, b):
        self.calls.append(("sub", (a, b)))
        return a - b

    def div(self, a, b):
        self.calls.append(("div", (a, b)))
        return a / b

    def negate(self, a):
        self.calls.append(("negate", (a,)))
        return -a

    def percent(self, a):
        self.calls.append(("percent", (a,)))
        return a / 100

    def sin(self, a, unit):
        self.calls.append(("sin", (a, unit)))
        return (a, unit)

    def pow(self, a, b):
        self.calls.append(("pow", (a, b)))
        return pow(a, b)

    def sqrt(self, a):
        self.calls.append(("sqrt", (a,)))
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


class FakeTokenKind:
    Number = "number"
    Op = "op"


class FakeArity(Enum):
    Unary = "unary"
    Binary = "binary"
    Postfix = "postfix"


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

    calc_native.OpId = SimpleNamespace(
        Sqrt=FakeOpId.SQRT,
        Asin=FakeOpId.ASIN,
        Acos=FakeOpId.ACOS,
        Acosh=FakeOpId.ACOSH,
        Atanh=FakeOpId.ATANH,
        Log=FakeOpId.LOG,
        Ln=FakeOpId.LN,
        Root=FakeOpId.ROOT,
    )

    def op_table():
        def entry(
            op_id: FakeOpId,
            symbol: str,
            arity: FakeArity,
            method: str,
            *,
            needs_unit: bool = False,
            big: bool = False,
            bigcx: bool = False,
        ):
            return (
                op_id,
                symbol,
                0,  # precedence 
                0,  # assoc
                arity,
                (),  # aliases
                method,
                needs_unit,
                big,
                bigcx,
            )

        return [
            entry(FakeOpId.ADD, "+", FakeArity.Binary, "add", big=True, bigcx=True),
            entry(FakeOpId.SUB, "-", FakeArity.Binary, "sub"),
            entry(FakeOpId.NEGATE, "u-", FakeArity.Unary, "negate"),
            entry(FakeOpId.PERCENT, "%", FakeArity.Postfix, "percent"),
            entry(FakeOpId.SIN, "sin", FakeArity.Unary, "sin", needs_unit=True),
            entry(FakeOpId.POW, "^", FakeArity.Binary, "pow", big=True, bigcx=True),
            entry(FakeOpId.SQRT, "sqrt", FakeArity.Unary, "sqrt", big=True, bigcx=True),
            entry(FakeOpId.LOG, "log", FakeArity.Unary, "log"),
        ]

    calc_native.op_table = op_table

    def _unavailable(*_args, **_kwargs):
        raise NotImplementedError("calc_native is faked in unit tests")

    calc_native.tokenize_string = _unavailable
    calc_native.shunting_yard = _unavailable

    calc_native.BigReal = FakeBigReal
    calc_native.BigComplex = FakeBigComplex
    calc_native.Calculator = DummyCalc
    calc_native.CalculatorError = FakeNativeCalculatorError
    return calc_native


# Ensure core modules can be imported without the real native extension.
sys.modules["calc_native"] = _install_fake_calc_native()



def _cx_sqrt(x: float) -> bool:
    return x < 0.0


def _cx_root(x: float, y: float) -> bool:
    return x < 0.0


def _cx_log(x: float) -> bool:
    return x <= 0.0


_FAKE_OP_SPECS: dict[FakeOpId, FakeSpec] = {
    FakeOpId.ADD: FakeSpec(arity="binary", method="add", big=True, bigcx=True),
    FakeOpId.SUB: FakeSpec(arity="binary", method="sub"),
    FakeOpId.NEGATE: FakeSpec(arity="unary", method="negate"),
    FakeOpId.PERCENT: FakeSpec(arity="unary", method="percent"),
    FakeOpId.SIN: FakeSpec(arity="unary", method="sin"),
    FakeOpId.POW: FakeSpec(arity="binary", method="pow", big=True, bigcx=True),
    FakeOpId.SQRT: FakeSpec(
         arity="unary", method="sqrt", cx=_cx_sqrt, big=True, bigcx=True
    ),
    FakeOpId.ROOT: FakeSpec(arity="binary", method="root", cx=_cx_root),
    FakeOpId.LOG: FakeSpec(arity="unary", method="log", cx=_cx_log),
    FakeOpId.BAD_TYPE: FakeSpec(arity="binary", method="bad_type"),
    FakeOpId.BAD_NATIVE: FakeSpec(arity="binary", method="bad_native"),
}


@pytest.fixture
def dummy_calc() -> DummyCalc:
    return DummyCalc()


@pytest.fixture
def token_factory() -> tuple[Callable[[object], FakeToken], Callable[[object], FakeToken]]:
    def num(value: object) -> FakeToken:
        return FakeToken(FakeTokenKind.Number, value=value)

    def op(op_id: object) -> FakeToken:
        return FakeToken(FakeTokenKind.Op, op_id=op_id)

    return num, op


@pytest.fixture
def fake_ops(monkeypatch) -> dict[FakeOpId, FakeSpec]:
    from tcalc.core import parser as parser_mod

    ops = {
        FakeOpId.ADD: FakeSpec(arity="binary", method="add", sym="+"),
        FakeOpId.SUB: FakeSpec(arity="binary", method="sub", sym="-"),
        FakeOpId.NEGATE: FakeSpec(arity="unary", method="negate", sym="u-"),
        FakeOpId.PERCENT: FakeSpec(arity="postfix", method="percent", sym="%"),
        FakeOpId.SIN: FakeSpec(arity="unary", method="sin", needs_unit=True, sym="sin"),
    }

    monkeypatch.setattr(parser_mod, "OP_BY_ID", ops)
    monkeypatch.setattr(
        parser_mod, "calc_native", SimpleNamespace(TokenKind=FakeTokenKind), raising=False
    )
    monkeypatch.setattr(parser_mod, "is_number_token", lambda tok: tok.kind == FakeTokenKind.Number)
    return ops


@pytest.fixture
def op_ids() -> type[FakeOpId]:
    return FakeOpId


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


@pytest.fixture
def fake_calc_native(monkeypatch):
    from tcalc.core import utils as utils_mod

    monkeypatch.setattr(
        utils_mod,
        "calc_native",
        SimpleNamespace(BigReal=FakeBigReal),
        raising=False,
    )


@pytest.fixture
def fake_engine(monkeypatch):
    from tcalc.core import engine as engine_mod

    monkeypatch.setattr(engine_mod, "Operation", FakeOpId)
    return engine_mod


_CANONICAL_CONFTST = "tests.py.unit.core.conftest"
if __name__ != _CANONICAL_CONFTST:
    sys.modules.setdefault(_CANONICAL_CONFTST, sys.modules[__name__])
