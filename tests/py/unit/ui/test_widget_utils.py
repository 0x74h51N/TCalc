#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QWidget
from pytest import param


@dataclass(frozen=True, slots=True)
class FitRadiusCase:
    radius: int
    side: int
    applied: int | None
    expected: int
    sheet: str


@pytest.mark.parametrize(
    "case",
    [
        param(FitRadiusCase(4, 20, None, 4, "x { border-radius: 4px; }"), id="fits"),
        param(FitRadiusCase(99, 20, None, 10, "x { border-radius: 10px; }"), id="capped"),
        param(FitRadiusCase(99, 20, 10, 10, ""), id="already applied"),
    ],
)
@pytest.mark.usefixtures("qapp")
def test_fit_radius(case):
    from tcalc.ui.widgets.utils import fit_radius

    widget = QWidget()
    assert fit_radius(widget, "x", case.radius, case.side, case.applied) == case.expected
    assert widget.styleSheet() == case.sheet


@pytest.mark.usefixtures("qapp")
def test_shortest_side_takes_the_smallest_shown_widget():
    from tcalc.ui.widgets.utils import shortest_side

    wide, narrow, hidden = QWidget(), QWidget(), QWidget()
    wide.resize(100, 50)
    narrow.resize(20, 100)
    hidden.resize(5, 5)
    wide.show()
    narrow.show()
    assert shortest_side([wide, narrow, hidden]) == 20


def test_shortest_side_of_nothing_is_none():
    from tcalc.ui.widgets.utils import shortest_side

    assert shortest_side([]) is None


@pytest.fixture
def fake_prop(monkeypatch):
    monkeypatch.setattr("tcalc.ui.widgets.utils.Prop", SimpleNamespace(RAISED="raised"))


@pytest.mark.usefixtures("qapp", "fake_prop")
def test_set_raised_sets_the_property():
    from tcalc.ui.widgets.utils import set_raised

    widget = QWidget()
    set_raised(widget, True)
    assert widget.property("raised") is True


class FakeRaisedContainer:
    def __init__(self):
        self.set = []

    def property(self, _name):
        return True

    def setProperty(self, name, value):
        self.set.append((name, value))


@pytest.mark.usefixtures("fake_prop")
def test_set_raised_does_nothing_when_already_so():
    from tcalc.ui.widgets.utils import set_raised

    container = FakeRaisedContainer()
    set_raised(container, True)
    assert container.set == []


@pytest.mark.parametrize(
    ("side", "expected"),
    [
        param(50, 8, id="small takes min"),
        param(300, 16, id="between"),
        param(1000, 24, id="large takes max"),
    ],
)
@pytest.mark.usefixtures("qapp")
def test_apply_scaled_fonts(side, expected):
    from tcalc.ui.widgets.utils import apply_scaled_fonts

    sample, target = QWidget(), QWidget()
    sample.resize(side, side)
    apply_scaled_fonts(sample, target, 8, 24)
    assert target.font().pointSize() == expected


@pytest.mark.usefixtures("qapp")
def test_apply_scaled_fonts_takes_many_targets():
    from tcalc.ui.widgets.utils import apply_scaled_fonts

    sample, targets = QWidget(), [QWidget(), QWidget()]
    sample.resize(50, 50)
    apply_scaled_fonts(sample, targets, 8, 24)
    assert [t.font().pointSize() for t in targets] == [8, 8]


@pytest.mark.usefixtures("qapp")
def test_a_lone_min_above_the_default_max_never_scales_backwards():
    # [history.result] font = { min_pt = 20 } keeps the default max_pt = 12
    from tcalc.ui.widgets.utils import apply_scaled_fonts

    sample, target = QWidget(), QWidget()
    sample.resize(2000, 2000)
    apply_scaled_fonts(sample, target, 20, 12)
    assert target.font().pointSize() == 20


@pytest.fixture
def key_radius_parts(monkeypatch):
    """A theme radius of 8; a fit answers what it was asked."""
    keypad = SimpleNamespace(button=SimpleNamespace(radius=8))
    theme = SimpleNamespace(look=SimpleNamespace(keypad=keypad))
    monkeypatch.setattr("tcalc.ui.widgets.utils.get_theme", lambda: theme)
    monkeypatch.setattr(
        "tcalc.ui.widgets.utils.fit_radius",
        lambda _container, _selector, radius, side, applied: ("fit", radius, side, applied),
    )


@pytest.mark.usefixtures("key_radius_parts")
def test_apply_key_radius_fits_to_the_shortest_key(monkeypatch):
    from tcalc.ui.widgets.utils import apply_key_radius

    monkeypatch.setattr("tcalc.ui.widgets.utils.shortest_side", lambda _keys: 20)
    assert apply_key_radius("container", [], 5) == ("fit", 8, 20, 5)


@pytest.mark.usefixtures("key_radius_parts")
def test_apply_key_radius_with_no_keys_keeps_what_it_had(monkeypatch):
    from tcalc.ui.widgets.utils import apply_key_radius

    monkeypatch.setattr("tcalc.ui.widgets.utils.shortest_side", lambda _keys: None)
    assert apply_key_radius("container", [], 5) == 5


@dataclass(frozen=True, slots=True)
class ShrinkCase:
    side: int | None
    applied: int | None
    expected: object


@pytest.mark.parametrize(
    "case",
    [
        param(ShrinkCase(10, 8, ("fit", 8, 10, 8)), id="keys shrank below the radius"),
        param(ShrinkCase(40, 8, 8), id="still fits"),
        param(ShrinkCase(None, 8, 8), id="no keys"),
        param(ShrinkCase(10, None, None), id="before the first fit"),
    ],
)
@pytest.mark.usefixtures("key_radius_parts")
def test_shrink_key_radius(monkeypatch, case):
    from tcalc.ui.widgets.utils import shrink_key_radius

    monkeypatch.setattr("tcalc.ui.widgets.utils.shortest_side", lambda _keys: case.side)
    assert shrink_key_radius("container", [], case.applied) == case.expected
