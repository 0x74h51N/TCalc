#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from dataclasses import astuple
from dataclasses import dataclass
from types import SimpleNamespace
from typing import NewType

import pytest
from pytest import param

FakeColor = NewType("FakeColor", str)


@dataclass
class FakeTinted:
    color: str
    opacity: float


FakeRef = FakeColor | FakeTinted


@dataclass
class FakeInner:
    color: FakeColor


@dataclass
class FakeTable:
    color: FakeColor
    bare: FakeRef
    tinted: FakeRef
    size: int
    inner: FakeInner


class FakeError(Exception):
    pass


class FakeButton:
    pass


@dataclass
class FakeArea:
    button: FakeButton
    number: FakeButton
    size: int


def test_look_fields(monkeypatch):
    from tcalc.ui.look import look_fields

    monkeypatch.setattr("tcalc.ui.look.ColorName", FakeColor)
    monkeypatch.setattr("tcalc.ui.look.ColorRef", FakeRef)
    monkeypatch.setattr("tcalc.ui.look.Tinted", FakeTinted)
    table = FakeTable("a", "b", FakeTinted("c", 0.5), 7, FakeInner("d"))
    assert [astuple(f) for f in look_fields(table)] == [
        (("color",), "a", 1.0),
        (("bare",), "b", 1.0),
        (("tinted",), "c", 0.5),
        (("size",), 7),
        (("inner", "color"), "d", 1.0),
    ]


def test_qss_name():
    from tcalc.ui.look import qss_name

    assert qss_name(SimpleNamespace(path=("a", "b"))) == "a_b"


def test_tinted_takes_an_opacity_in_range():
    from tcalc.ui.look import Tinted

    assert Tinted("a", 0.5).opacity == 0.5


def test_tinted_refuses_an_opacity_above_one(monkeypatch):
    from tcalc.ui.look import Tinted

    monkeypatch.setattr("tcalc.ui.look.TableError", FakeError)
    with pytest.raises(FakeError):
        Tinted("a", 1.5)


@dataclass(frozen=True, slots=True)
class MergedCase:
    base: object
    over: object
    expected: object


@pytest.mark.parametrize(
    "case",
    [
        param(
            MergedCase({"a": 1, "b": {"c": 1}}, {"b": {"d": 2}}, {"a": 1, "b": {"c": 1, "d": 2}}),
            id="tables",
        ),
        param(
            MergedCase({"color": "a", "opacity": 0.5}, {"color": "b"}, {"color": "b"}),
            id="opacity whole",
        ),
        param(MergedCase(1, 2, 2), id="not tables"),
    ],
)
def test_merged(case):
    from tcalc.ui.look import _merged

    assert _merged(case.base, case.over) == case.expected


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        param({"color": "a"}, {"color": "a", "hover_color": "a"}, id="follows"),
        param({"color": "a", "hover_color": "b"}, {"color": "a", "hover_color": "b"}, id="own"),
        param(5, 5, id="not a table"),
    ],
)
def test_hover_follows_color(key, expected):
    from tcalc.ui.look import _hover_follows_color

    assert _hover_follows_color(key) == expected


@pytest.mark.parametrize(
    ("table", "expected"),
    [
        param(
            {"keypad": {"button": {"color": "a"}, "number": {"size": 1}, "size": 2}},
            {
                "keypad": {
                    "button": {"color": "a", "hover_color": "a"},
                    "number": {"color": "a", "size": 1, "hover_color": "a"},
                    "size": 2,
                },
                "history": {},
            },
            id="keypad button reaches the key",
        ),
        param(
            {"history": {"button": {"color": "a"}}},
            {
                "keypad": {},
                "history": {"button": {"color": "a"}, "number": {"color": "a"}},
            },
            id="history button reaches the area",
        ),
        param(
            {"keypad": {"button": {"color": "a"}, "number": {"color": "b"}}},
            {
                "keypad": {
                    "button": {"color": "a", "hover_color": "a"},
                    "number": {"color": "b", "hover_color": "b"},
                },
                "history": {},
            },
            id="own value wins",
        ),
        param({"keypad": [1]}, {"keypad": [1], "history": {}}, id="area not a table"),
    ],
)
def test_with_shared_buttons(monkeypatch, table, expected):
    from tcalc.ui.look import with_shared_buttons

    monkeypatch.setattr("tcalc.ui.look.KeypadLook", FakeArea)
    monkeypatch.setattr("tcalc.ui.look.HistoryLook", FakeArea)
    monkeypatch.setattr("tcalc.ui.look.Button", FakeButton)
    assert with_shared_buttons(table) == expected
