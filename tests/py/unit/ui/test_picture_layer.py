#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QRect, QSize
from PySide6.QtWidgets import QListWidget, QWidget

from tcalc.theme import PictureFit, PicturePosition, PictureTarget, ThemePicture, load_theme
from tcalc.ui.widgets.common import picture_layer
from tcalc.ui.widgets.common.picture_layer import PictureLayer, picture_rects


def test_config_defaults():
    picture = ThemePicture.from_config(Path("t"), {"file": "a.svg", "target": "display"})
    assert picture == ThemePicture(Path("t/a.svg"), PictureTarget.DISPLAY)


def test_top_right_contain_sits_in_the_corner_inside_the_margin():
    picture = ThemePicture(
        Path("a.svg"), PictureTarget.DISPLAY, PicturePosition.TOP_RIGHT, size=0.5, margin=10
    )
    box, rect = picture_rects(picture, QRect(0, 0, 420, 220), QSize(100, 100))
    assert box == QRect(210, 10, 200, 100)
    assert rect == QRect(310, 10, 100, 100)  # square kept, pushed right


def test_cover_overflows_its_box():
    picture = ThemePicture(Path("a.svg"), PictureTarget.DISPLAY, fit=PictureFit.COVER)
    box, rect = picture_rects(picture, QRect(0, 0, 200, 100), QSize(100, 100))
    assert box == QRect(0, 0, 200, 100) and rect.size() == QSize(200, 200)


def test_component_smaller_than_the_margins_gives_an_empty_box():
    picture = ThemePicture(Path("a.svg"), PictureTarget.DISPLAY, margin=10)
    box, rect = picture_rects(picture, QRect(0, 0, 15, 15), QSize(100, 100))
    assert box.size() == QSize(0, 0) and rect.size() == QSize(0, 0)


def test_empty_box_is_not_rendered(qtbot, monkeypatch):
    svg = Path(__file__).parents[4] / "assets" / "icons" / "accessories-calculator.svg"
    picture = ThemePicture(svg, PictureTarget.DISPLAY, margin=10)
    monkeypatch.setattr(picture_layer, "get_theme", lambda: SimpleNamespace(pictures=(picture,)))
    rendered = []
    monkeypatch.setattr(picture_layer, "_render", lambda p, s: rendered.append(s))
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.resize(15, 15)
    PictureLayer(widget, PictureTarget.DISPLAY).grab()
    assert rendered == []


@pytest.fixture
def sponge():
    load_theme("sponge")
    yield
    load_theme("dark")


@pytest.mark.usefixtures("sponge")
def test_resizing_renders_the_picture_again_only_once_it_settles(qtbot, monkeypatch):
    sizes = []
    render = picture_layer._render
    monkeypatch.setattr(
        picture_layer, "_render", lambda p, s: sizes.append(s.toTuple()) or render(p, s)
    )
    window = QWidget()
    qtbot.addWidget(window)
    window.resize(400, 200)
    layer = PictureLayer(window, PictureTarget.WINDOW)
    layer.grab()
    for width in (420, 440, 460):
        window.resize(width, 200)
        layer.grab()
    assert len(sizes) == 1  # stretched while resizing
    qtbot.wait(300)
    layer.grab()
    assert sizes[-1][0] == 460


def test_layer_stays_in_place_while_its_owner_scrolls(qtbot):
    lst = QListWidget()
    qtbot.addWidget(lst)
    lst.addItems([str(i) for i in range(100)])
    lst.resize(200, 200)
    layer = PictureLayer(lst.viewport(), PictureTarget.HISTORY)
    lst.show()
    lst.verticalScrollBar().setValue(20)
    assert layer.geometry() == lst.viewport().rect()
