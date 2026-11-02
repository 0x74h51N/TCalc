#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import dataclasses
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QRect, QSize, QThreadPool
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QListWidget, QWidget
from pytest import param

from tcalc.theme import (
    PictureFit,
    PicturePosition,
    PictureTarget,
    ThemePicture,
    get_theme,
    load_theme,
)
from tcalc.ui.utils import ICONS_DIR
from tcalc.ui.widgets.common import picture_layer
from tcalc.ui.widgets.common.picture_layer import (
    LOW_RES_DIVISOR,
    PictureLayer,
    master_size,
    picture_rects,
)


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
    svg = ICONS_DIR / "accessories-calculator.svg"
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


def window_picture() -> ThemePicture:
    return [p for p in get_theme().pictures if p.target is PictureTarget.WINDOW][0]


def record_renders(
    monkeypatch, hold_full: threading.Event | None = None
) -> list[tuple[tuple[int, int], int]]:
    """Each _render call's size and thread; with *hold_full*, every call after the first waits."""
    calls: list[tuple[tuple[int, int], int]] = []
    render = picture_layer._render

    def recording(picture: ThemePicture, size: QSize):
        first = not calls
        calls.append((size.toTuple(), threading.get_ident()))
        if hold_full is not None and not first:
            hold_full.wait(5)
        return render(picture, size)

    monkeypatch.setattr(picture_layer, "_render", recording)
    return calls


def sponge_window_layer(qtbot, width: int, height: int) -> tuple[QWidget, PictureLayer]:
    window = QWidget()
    qtbot.addWidget(window)
    window.resize(width, height)
    return window, PictureLayer(window, PictureTarget.WINDOW)


def layer_image_rect(layer: PictureLayer) -> QRect:
    picture = window_picture()
    return picture_rects(picture, layer.rect(), picture_layer._natural_size(picture.file))[1]


@pytest.mark.usefixtures("sponge")
@pytest.mark.parametrize(
    "fit, size, screen, expected",
    [
        param(PictureFit.COVER, 1.0, QSize(3440, 1440), QSize(3440, 1720), id="full screen cover"),
        param(PictureFit.COVER, 0.5, QSize(1000, 600), QSize(600, 300), id="half box cover"),
        param(PictureFit.CONTAIN, 1.0, QSize(3440, 1440), QSize(2880, 1440), id="contain fits in"),
        param(
            PictureFit.STRETCH, 1.0, QSize(3440, 1440), QSize(3440, 1440), id="stretch is the box"
        ),
    ],
)
def test_master_size_is_the_largest_drawn_size_on_the_screen(fit, size, screen, expected):
    # Sponge's window picture is undersea.svg, natural size 600x300
    picture = dataclasses.replace(window_picture(), fit=fit, size=size)
    assert master_size(picture, screen) == expected


@pytest.mark.usefixtures("sponge")
def test_render_runs_off_the_main_thread_and_resizing_only_scales(qtbot, monkeypatch):
    calls = record_renders(monkeypatch)
    window, layer = sponge_window_layer(qtbot, 400, 200)
    layer.grab()
    qtbot.waitUntil(lambda: len(calls) == 2)  # low resolution, then full
    qtbot.waitUntil(lambda: picture_layer.QThreadPool.globalInstance().activeThreadCount() == 0)
    assert all(thread != threading.get_ident() for _, thread in calls)
    for width in (420, 440, 460):
        window.resize(width, 200)
        layer.grab()
    assert len(calls) == 2
    assert layer._pictures._cache[window_picture()].size() == layer_image_rect(layer).size()


@pytest.mark.usefixtures("sponge")
def test_low_resolution_is_drawn_before_the_full_one(qtbot, monkeypatch):
    full = threading.Event()
    calls = record_renders(monkeypatch, hold_full=full)
    window, layer = sponge_window_layer(qtbot, 400, 200)
    layer.grab()
    qtbot.waitUntil(lambda: window_picture() in layer._pictures._masters)
    key, image = layer._pictures._masters[window_picture()]
    assert image.size() == QSize(key[0] // LOW_RES_DIVISOR, key[1] // LOW_RES_DIVISOR)
    window.resize(460, 200)
    layer.grab()
    assert len(calls) == 2  # the low pass and the held full pass, no new job
    full.set()
    qtbot.waitUntil(lambda: layer._pictures._masters[window_picture()][1].size() == QSize(*key))


def test_raster_picture_is_read_once_at_full_size(qtbot, monkeypatch, tmp_path):
    png = tmp_path / "picture.png"
    image = QImage(QSize(64, 32), QImage.Format.Format_RGB32)
    image.fill(0)
    assert image.save(str(png))
    picture = ThemePicture(png, PictureTarget.WINDOW, fit=PictureFit.COVER)
    monkeypatch.setattr(picture_layer, "get_theme", lambda: SimpleNamespace(pictures=(picture,)))
    calls = record_renders(monkeypatch)
    _window, layer = sponge_window_layer(qtbot, 400, 200)
    layer.grab()
    wait_for_renders(qtbot)
    assert [size for size, _ in calls] == [layer._pictures._masters[picture][0]]


def wait_for_renders(qtbot) -> None:
    QThreadPool.globalInstance().waitForDone()
    qtbot.wait(50)  # the queued results reach the painter


@pytest.mark.usefixtures("sponge")
def test_result_of_the_previous_theme_is_never_drawn(qtbot, monkeypatch):
    full = threading.Event()
    record_renders(monkeypatch, hold_full=full)
    _window, layer = sponge_window_layer(qtbot, 400, 200)
    layer.grab()
    load_theme("kitty")
    layer.grab()
    full.set()
    wait_for_renders(qtbot)
    assert layer._pictures._masters == {}  # Kitty has no window picture


@pytest.mark.usefixtures("sponge")
def test_widget_closed_while_rendering_raises_nothing(qtbot, monkeypatch):
    full = threading.Event()
    record_renders(monkeypatch, hold_full=full)
    window = QWidget()
    window.resize(400, 200)
    layer = PictureLayer(window, PictureTarget.WINDOW)
    with qtbot.captureExceptions() as exceptions:
        layer.grab()
        window.close()
        window.deleteLater()
        qtbot.wait(10)
        full.set()
        wait_for_renders(qtbot)
    assert not exceptions


@pytest.mark.usefixtures("sponge")
def test_screen_of_another_size_renders_a_new_master(qtbot, monkeypatch):
    calls = record_renders(monkeypatch)
    _window, layer = sponge_window_layer(qtbot, 400, 200)
    layer.grab()
    qtbot.waitUntil(lambda: len(calls) == 2)
    wait_for_renders(qtbot)
    old_key = layer._pictures._masters[window_picture()][0]
    full = threading.Event()
    monkeypatch.setattr(picture_layer, "master_size", lambda _p, _s: QSize(2000, 1000))
    record_renders(monkeypatch, hold_full=full)
    layer.grab()
    qtbot.wait(100)  # the new low pass arrives, the full one is held
    assert layer._pictures._masters[window_picture()][0] == old_key  # sharp until the new one
    full.set()
    wait_for_renders(qtbot)
    assert layer._pictures._masters[window_picture()][0] == (2000, 1000)


def test_layer_stays_in_place_while_its_owner_scrolls(qtbot):
    lst = QListWidget()
    qtbot.addWidget(lst)
    lst.addItems([str(i) for i in range(100)])
    lst.resize(200, 200)
    layer = PictureLayer(lst.viewport(), PictureTarget.HISTORY)
    lst.show()
    lst.verticalScrollBar().setValue(20)
    assert layer.geometry() == lst.viewport().rect()
