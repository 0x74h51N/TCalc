#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QWidget
from pytest import param


def _arm(table, name):
    return next(arm for key, arm in table.items() if key.name == name)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        param("LEFT", 5, id="left"),
        param("CENTER", 180, id="center"),
        param("RIGHT", 355, id="right"),
    ],
)
def test_horizontal_arm(name, expected):
    from tcalc.ui.widgets.common.utils import _H_ALGN

    assert _arm(_H_ALGN, name)(400, 40, 5) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        param("TOP", 5, id="top"),
        param("CENTER", 140, id="center"),
        param("BOTTOM", 275, id="bottom"),
    ],
)
def test_vertical_arm(name, expected):
    from tcalc.ui.widgets.common.utils import _V_ALGN

    assert _arm(_V_ALGN, name)(300, 20, 5) == expected


@pytest.fixture
def fake_arms(monkeypatch):
    monkeypatch.setattr(
        "tcalc.ui.widgets.common.utils._H_ALGN", {"h": lambda pw, ww, m: pw - ww + m}
    )
    monkeypatch.setattr(
        "tcalc.ui.widgets.common.utils._V_ALGN", {"v": lambda ph, wh, m: ph - wh - m}
    )


@pytest.mark.usefixtures("qapp", "fake_arms")
def test_reposition_moves_by_the_arms_it_names():
    from tcalc.ui.widgets.common.utils import reposition

    parent = QWidget()
    parent.resize(400, 300)
    child = QWidget(parent)
    child.resize(40, 20)
    reposition(child, "h", "v", 5)
    assert child.pos() == QPoint(365, 275)


@pytest.mark.usefixtures("qapp", "fake_arms")
def test_reposition_without_a_parent_stays_where_it_is():
    from tcalc.ui.widgets.common.utils import reposition

    orphan = QWidget()
    orphan.move(3, 4)
    reposition(orphan, "h", "v", 5)
    assert orphan.pos() == QPoint(3, 4)
