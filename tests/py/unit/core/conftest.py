from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import SimpleNamespace
from typing import Callable

import pytest


@dataclass(frozen=True)
class FakeToken:
    kind: object
    op_id: object | None = None
    value: object | None = None


@dataclass(frozen=True)
class FakeSpec:
    arity: str
    method: str
    needs_unit: bool = False
    sym: str = ""


class DummyCalc:
    def add(self, a, b):
        return a + b

    def sub(self, a, b):
        return a - b

    def negate(self, a):
        return -a

    def percent(self, a):
        return a / 100

    def sin(self, a, unit):
        return (a, unit)


class FakeBigReal:
    def __init__(self, value: str):
        self.value = str(value)

    def __str__(self) -> str:
        return self.value


class FakeBigRealFail:
    def __init__(self, value: str):
        raise ValueError(f"bad BigReal: {value}")


class FakeTokenKind:
    Number = "number"
    Op = "op"


class FakeOpId(Enum):
    ADD = "add"
    SUB = "sub"
    NEGATE = "negate"
    PERCENT = "percent"
    SIN = "sin"
    CEKOMASTIK = "cekomastik"


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
