#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import NewType

import pytest
from pytest import param

FakeName = NewType("FakeName", str)


class FakeError(Exception):
    pass


class FakeFit(Enum):
    CONTAIN = "contain"
    COVER = "cover"


@dataclass(frozen=True, slots=True)
class FakeInner:
    n: int
    k: int


@dataclass(frozen=True, slots=True)
class FakeOuter:
    inner: FakeInner
    opt: str = "x"


@pytest.fixture(autouse=True)
def fake_error(monkeypatch):
    monkeypatch.setattr("tcalc.typed_tables.TableError", FakeError)


def _messages(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records]


def _patch_convert_keys(monkeypatch, converted, errors) -> None:
    monkeypatch.setattr(
        "tcalc.typed_tables._convert_keys",
        lambda _table, _hint_of, _convert, _where: (converted, errors),
    )


def _calling_convert_keys(table, hint_of, convert, where):
    return {k: convert(k, v, hint_of(k), f"{where}.{k}") for k, v in table.items()}, []


def test_build_makes_the_class(monkeypatch):
    from tcalc.typed_tables import build

    _patch_convert_keys(monkeypatch, {"n": 1, "k": 2}, [])
    assert build(FakeInner, {}, "w") == FakeInner(1, 2)


def test_build_leaves_a_default_to_the_class(monkeypatch):
    from tcalc.typed_tables import build

    _patch_convert_keys(monkeypatch, {"inner": 1}, [])
    assert build(FakeOuter, {}, "w") == FakeOuter(1, "x")


def test_build_raises_on_a_missing_key(monkeypatch):
    from tcalc.typed_tables import build

    _patch_convert_keys(monkeypatch, {"n": 1}, [])
    with pytest.raises(FakeError, match="w.k: missing"):
        build(FakeInner, {}, "w")


def test_build_raises_the_first_error(monkeypatch):
    from tcalc.typed_tables import build

    _patch_convert_keys(monkeypatch, {}, [FakeError("first"), FakeError("second")])
    with pytest.raises(FakeError, match="first"):
        build(FakeInner, {}, "w")


def test_override_applies_a_key(monkeypatch):
    from tcalc.typed_tables import override

    monkeypatch.setattr("tcalc.typed_tables._convert_keys", _calling_convert_keys)
    monkeypatch.setattr("tcalc.typed_tables._convert", lambda value, _hint, _where: value)
    assert override(FakeInner(1, 2), {"n": 5}, "w") == FakeInner(5, 2)


def test_override_a_nested_table_names_only_some_fields(monkeypatch):
    from tcalc.typed_tables import override

    monkeypatch.setattr("tcalc.typed_tables._convert_keys", _calling_convert_keys)
    monkeypatch.setattr("tcalc.typed_tables._convert", lambda value, _hint, _where: value)
    table = FakeOuter(FakeInner(1, 2))
    assert override(table, {"inner": {"n": 7}}, "w") == FakeOuter(FakeInner(7, 2))


def test_override_logs_a_bad_key_and_keeps_the_rest(monkeypatch, caplog):
    from tcalc.typed_tables import override

    _patch_convert_keys(monkeypatch, {"n": 5}, [FakeError("w.z: unknown key")])
    with caplog.at_level(logging.WARNING):
        assert override(FakeInner(1, 2), {}, "w") == FakeInner(5, 2)
    assert _messages(caplog) == ["w.z: unknown key"]


def test_values_keeps_one_kind(monkeypatch):
    from tcalc.typed_tables import values

    monkeypatch.setattr("tcalc.typed_tables._convert_keys", _calling_convert_keys)
    assert values({"a": "x"}, str, "w") == {"a": "x"}


def test_values_refuses_another_kind(monkeypatch):
    from tcalc.typed_tables import values

    monkeypatch.setattr("tcalc.typed_tables._convert_keys", _calling_convert_keys)
    with pytest.raises(FakeError, match="w.b: expected str, got int"):
        values({"b": 5}, str, "w")


def test_values_logs_what_was_refused(monkeypatch, caplog):
    from tcalc.typed_tables import values

    _patch_convert_keys(monkeypatch, {"a": "x"}, [FakeError("bad")])
    with caplog.at_level(logging.WARNING):
        assert values({}, str, "w") == {"a": "x"}
    assert _messages(caplog) == ["bad"]


def _doubled(_key, value, _hint, _at):
    return value * 2


def _refused(_key, _value, _hint, at):
    raise FakeError(f"{at}: refused")


def test_convert_keys_converts_a_table():
    from tcalc.typed_tables import _convert_keys

    assert _convert_keys({"a": 2}, {"a": int}.get, _doubled, "w") == ({"a": 4}, [])


def test_convert_keys_refuses_what_is_not_a_table():
    from tcalc.typed_tables import _convert_keys

    converted, errors = _convert_keys([1], {}.get, _doubled, "w")
    assert converted == {} and [str(e) for e in errors] == ["w: expected a table, got list"]


def test_convert_keys_reports_an_unknown_key():
    from tcalc.typed_tables import _convert_keys

    converted, errors = _convert_keys({"a": 2, "z": 1}, {"a": int}.get, _doubled, "w")
    assert converted == {"a": 4} and [str(e) for e in errors] == ["w.z: unknown key"]


def test_convert_keys_reports_what_convert_refuses():
    from tcalc.typed_tables import _convert_keys

    converted, errors = _convert_keys({"a": 2}, {"a": int}.get, _refused, "w")
    assert converted == {} and [str(e) for e in errors] == ["w.a: refused"]


@dataclass(frozen=True, slots=True)
class ConvertCase:
    value: object
    hint: object
    expected: object


@pytest.mark.parametrize(
    "case",
    [
        param(ConvertCase("m", FakeName, "m"), id="new type"),
        param(ConvertCase({"n": 1}, FakeInner, ("built", FakeInner)), id="dataclass"),
        param(ConvertCase(1, int | str, 1), id="union first arm"),
        param(ConvertCase("a", int | str, "a"), id="union second arm"),
        param(ConvertCase(["p", "q"], tuple[str, ...], ("p", "q")), id="tuple"),
        param(ConvertCase("cover", FakeFit, ("enum", FakeFit)), id="enum"),
        param(ConvertCase(2, float, 2.0), id="int for float"),
        param(ConvertCase("a", Path, Path("a")), id="path"),
        param(ConvertCase(1, int, 1), id="scalar"),
    ],
)
def test_convert(monkeypatch, case):
    from tcalc.typed_tables import _convert

    monkeypatch.setattr("tcalc.typed_tables.build", lambda cls, _table, _where: ("built", cls))
    monkeypatch.setattr("tcalc.typed_tables._enum", lambda _value, enum, _where: ("enum", enum))
    result = _convert(case.value, case.hint, "w")
    assert result == case.expected and type(result) is type(case.expected)


@dataclass(frozen=True, slots=True)
class ConvertErrorCase:
    value: object
    hint: object
    message: str


@pytest.mark.parametrize(
    "case",
    [
        param(ConvertErrorCase(1.5, int | str, "w: expected int or str, got float"), id="union"),
        param(ConvertErrorCase("a", tuple[str, ...], "w: expected a list, got str"), id="tuple"),
        param(ConvertErrorCase("1", int, "w: expected int, got str"), id="scalar"),
        param(ConvertErrorCase(True, int, "w: expected int, got bool"), id="bool for int"),
    ],
)
def test_convert_refuses(case):
    from tcalc.typed_tables import _convert

    with pytest.raises(FakeError, match=case.message):
        _convert(case.value, case.hint, "w")


@pytest.mark.parametrize(
    ("value", "member"),
    [
        param("cover", FakeFit.COVER, id="by value"),
        param("COVER", FakeFit.COVER, id="by name"),
    ],
)
def test_enum(value, member):
    from tcalc.typed_tables import _enum

    assert _enum(value, FakeFit, "w") is member


@pytest.mark.parametrize("value", [param("fill", id="unknown name"), param(5, id="not text")])
def test_enum_refuses(value):
    from tcalc.typed_tables import _enum

    with pytest.raises(FakeError, match=f"w: expected FakeFit, got {type(value).__name__}"):
        _enum(value, FakeFit, "w")


@pytest.mark.parametrize(
    ("hint", "expected"),
    [
        param(FakeInner, True, id="dataclass"),
        param(int, False, id="class"),
        param(FakeInner(1, 2), False, id="an instance"),
    ],
)
def test_is_dataclass_type(hint, expected):
    from tcalc.typed_tables import is_dataclass_type

    assert is_dataclass_type(hint) is expected


def test_log_all(caplog):
    from tcalc.typed_tables import _log_all

    with caplog.at_level(logging.WARNING):
        _log_all([FakeError("a"), FakeError("b")])
    assert _messages(caplog) == ["a", "b"]
