#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import threading
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QRect
from PySide6.QtCore import QSize
from PySide6.QtCore import Qt
from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QColor
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QListWidget
from PySide6.QtWidgets import QWidget
from pytest import param

LOW_RES_DIVISOR = 4
NATURAL = QSize(600, 300)
WINDOW = "window target"
DISPLAY = "display target"
HISTORY = "history target"


@dataclass(frozen=True, slots=True)
class FakePosition:
    alignment: Qt.AlignmentFlag


@dataclass(frozen=True, slots=True)
class FakeFit:
    aspect_mode: Qt.AspectRatioMode


CENTER = FakePosition(Qt.AlignmentFlag.AlignCenter)
TOP_RIGHT = FakePosition(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
CONTAIN = FakeFit(Qt.AspectRatioMode.KeepAspectRatio)
COVER = FakeFit(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
STRETCH = FakeFit(Qt.AspectRatioMode.IgnoreAspectRatio)


@dataclass(frozen=True, slots=True)
class FakePicture:
    file: Path
    target: str
    position: FakePosition = CENTER
    size: float = 1.0
    fit: FakeFit = CONTAIN
    opacity: float = 1.0
    margin: int = 0
    tint: str = ""


@pytest.fixture
def svg(tmp_path) -> Path:
    """A picture file of natural size 600x300."""
    path = tmp_path / "picture.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300">'
        '<rect width="600" height="300"/></svg>'
    )
    return path


@pytest.fixture
def natural(monkeypatch) -> None:
    monkeypatch.setattr(
        "tcalc.ui.widgets.common.picture_layer._natural_size", lambda _file: NATURAL
    )


@pytest.fixture
def theme(svg, natural, monkeypatch) -> SimpleNamespace:
    """A theme with one window picture."""
    dummy = SimpleNamespace(pictures=(FakePicture(svg, WINDOW, fit=COVER),))
    monkeypatch.setattr("tcalc.ui.widgets.common.picture_layer.get_theme", lambda: dummy)
    monkeypatch.setattr("tcalc.ui.widgets.common.picture_layer.LOW_RES_DIVISOR", LOW_RES_DIVISOR)
    return dummy


def test_top_right_contain_sits_in_the_corner_inside_the_margin():
    from tcalc.ui.widgets.common.picture_layer import picture_rects

    picture = FakePicture(Path("a.svg"), DISPLAY, TOP_RIGHT, size=0.5, margin=10)
    box, rect = picture_rects(picture, QRect(0, 0, 420, 220), QSize(100, 100))
    assert box == QRect(210, 10, 200, 100)
    assert rect == QRect(310, 10, 100, 100)  # square kept, pushed right


def test_cover_overflows_its_box():
    from tcalc.ui.widgets.common.picture_layer import picture_rects

    picture = FakePicture(Path("a.svg"), DISPLAY, fit=COVER)
    box, rect = picture_rects(picture, QRect(0, 0, 200, 100), QSize(100, 100))
    assert box == QRect(0, 0, 200, 100) and rect.size() == QSize(200, 200)


def test_component_smaller_than_the_margins_gives_an_empty_box():
    from tcalc.ui.widgets.common.picture_layer import picture_rects

    picture = FakePicture(Path("a.svg"), DISPLAY, margin=10)
    box, rect = picture_rects(picture, QRect(0, 0, 15, 15), QSize(100, 100))
    assert box.size() == QSize(0, 0) and rect.size() == QSize(0, 0)


def test_natural_size_reads_the_file(svg):
    from tcalc.ui.widgets.common.picture_layer import _natural_size

    assert _natural_size(svg) == NATURAL


def test_render_reads_the_file_at_the_size(svg):
    from tcalc.ui.widgets.common.picture_layer import _render

    assert _render(FakePicture(svg, WINDOW), QSize(60, 30)).size() == QSize(60, 30)


def test_render_paints_the_tint_over_the_shape(monkeypatch, svg):
    from tcalc.ui.widgets.common.picture_layer import _render

    monkeypatch.setattr(
        "tcalc.ui.widgets.common.picture_layer.get_theme",
        lambda: SimpleNamespace(colors={"t": "#123456"}),
    )
    image = _render(FakePicture(svg, WINDOW, tint="t"), QSize(60, 30))
    assert image.pixelColor(30, 15) == QColor("#123456")


@pytest.mark.usefixtures("natural")
def test_empty_box_is_not_rendered(qtbot, monkeypatch, svg):
    from tcalc.ui.widgets.common.picture_layer import PictureLayer

    dummy = SimpleNamespace(pictures=(FakePicture(svg, DISPLAY, margin=10),))
    monkeypatch.setattr("tcalc.ui.widgets.common.picture_layer.get_theme", lambda: dummy)
    rendered = []
    monkeypatch.setattr(
        "tcalc.ui.widgets.common.picture_layer._render", lambda _p, s: rendered.append(s)
    )
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.resize(15, 15)
    PictureLayer(widget, DISPLAY).grab()
    QThreadPool.globalInstance().waitForDone()
    assert rendered == []


def record_renders(
    monkeypatch, hold_full: threading.Event | None = None
) -> list[tuple[tuple[int, int], int]]:
    """Each _render call's size and thread; with *hold_full*, every call after the first waits."""
    calls: list[tuple[tuple[int, int], int]] = []

    def recording(_picture, size: QSize):
        first = not calls
        calls.append((size.toTuple(), threading.get_ident()))
        if hold_full is not None and not first:
            hold_full.wait(5)
        image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0)
        return image

    monkeypatch.setattr("tcalc.ui.widgets.common.picture_layer._render", recording)
    return calls


def window_layer(qtbot, width: int, height: int):
    from tcalc.ui.widgets.common.picture_layer import PictureLayer

    window = QWidget()
    qtbot.addWidget(window)
    window.resize(width, height)
    return window, PictureLayer(window, WINDOW)


def wait_for_renders(qtbot) -> None:
    QThreadPool.globalInstance().waitForDone()
    qtbot.wait(50)  # the queued results reach the painter


@dataclass(frozen=True, slots=True)
class MasterSizeCase:
    fit: FakeFit
    size: float
    screen: QSize
    expected: QSize


@pytest.mark.usefixtures("natural")
@pytest.mark.parametrize(
    "case",
    [
        param(MasterSizeCase(COVER, 1.0, QSize(3440, 1440), QSize(3440, 1720)), id="full cover"),
        param(MasterSizeCase(COVER, 0.5, QSize(1000, 600), QSize(600, 300)), id="half box cover"),
        param(MasterSizeCase(CONTAIN, 1.0, QSize(3440, 1440), QSize(2880, 1440)), id="contain"),
        param(MasterSizeCase(STRETCH, 1.0, QSize(3440, 1440), QSize(3440, 1440)), id="stretch"),
    ],
)
def test_master_size_is_the_largest_drawn_size_on_the_screen(case):
    from tcalc.ui.widgets.common.picture_layer import master_size

    picture = FakePicture(Path("a.svg"), WINDOW, fit=case.fit, size=case.size)
    assert master_size(picture, case.screen) == case.expected


def test_render_runs_off_the_main_thread_and_resizing_only_scales(qtbot, monkeypatch, theme):
    calls = record_renders(monkeypatch)
    window, layer = window_layer(qtbot, 400, 200)
    layer.grab()
    qtbot.waitUntil(lambda: len(calls) == 2)  # low resolution, then full
    qtbot.waitUntil(lambda: QThreadPool.globalInstance().activeThreadCount() == 0)
    assert all(thread != threading.get_ident() for _, thread in calls)
    for width in (420, 440, 460):
        window.resize(width, 200)
        layer.grab()
    assert len(calls) == 2
    assert layer._pictures._cache[theme.pictures[0]].size() == QSize(460, 230)


def test_low_resolution_is_drawn_before_the_full_one(qtbot, monkeypatch, theme):
    picture = theme.pictures[0]
    full = threading.Event()
    calls = record_renders(monkeypatch, hold_full=full)
    window, layer = window_layer(qtbot, 400, 200)
    layer.grab()
    qtbot.waitUntil(lambda: picture in layer._pictures._masters)
    key, image = layer._pictures._masters[picture]
    assert image.size() == QSize(key[0] // LOW_RES_DIVISOR, key[1] // LOW_RES_DIVISOR)
    window.resize(460, 200)
    layer.grab()
    assert len(calls) == 2  # the low pass and the held full pass, no new job
    full.set()
    qtbot.waitUntil(lambda: layer._pictures._masters[picture][1].size() == QSize(*key))


def test_raster_picture_is_read_once_at_full_size(qtbot, monkeypatch, tmp_path, theme):
    png = tmp_path / "picture.png"
    image = QImage(QSize(64, 32), QImage.Format.Format_RGB32)
    image.fill(0)
    assert image.save(str(png))
    picture = FakePicture(png, WINDOW, fit=COVER)
    theme.pictures = (picture,)
    calls = record_renders(monkeypatch)
    _window, layer = window_layer(qtbot, 400, 200)
    layer.grab()
    wait_for_renders(qtbot)
    assert [size for size, _ in calls] == [layer._pictures._masters[picture][0]]


@pytest.mark.usefixtures("theme")
def test_result_of_the_previous_theme_is_never_drawn(qtbot, monkeypatch):
    full = threading.Event()
    record_renders(monkeypatch, hold_full=full)
    _window, layer = window_layer(qtbot, 400, 200)
    layer.grab()
    monkeypatch.setattr(
        "tcalc.ui.widgets.common.picture_layer.get_theme", lambda: SimpleNamespace(pictures=())
    )
    layer.grab()
    full.set()
    wait_for_renders(qtbot)
    assert layer._pictures._masters == {}


def test_a_picture_left_out_frees_its_images(qtbot, monkeypatch, theme):
    kept = theme.pictures[0]
    left_out = replace(kept, opacity=0.5)
    theme.pictures = (kept, left_out)
    record_renders(monkeypatch)
    _window, layer = window_layer(qtbot, 400, 200)
    layer.grab()
    wait_for_renders(qtbot)
    layer.grab()
    assert set(layer._pictures._masters) == set(layer._pictures._cache) == {kept, left_out}
    theme.pictures = (kept,)
    layer.grab()
    assert set(layer._pictures._masters) == set(layer._pictures._cache) == {kept}


def test_a_picture_left_out_while_rendering_is_not_kept(qtbot, monkeypatch, theme):
    kept = theme.pictures[0]
    left_out = replace(kept, opacity=0.5)
    theme.pictures = (kept, left_out)
    record_renders(monkeypatch)
    _window, layer = window_layer(qtbot, 400, 200)
    layer.grab()
    theme.pictures = (kept,)
    layer.grab()
    wait_for_renders(qtbot)
    assert set(layer._pictures._masters) == {kept}


def test_no_picture_left_frees_every_image(qtbot, monkeypatch, theme):
    record_renders(monkeypatch)
    _window, layer = window_layer(qtbot, 400, 200)
    layer.grab()
    wait_for_renders(qtbot)
    layer.grab()
    assert layer._pictures._masters and layer._pictures._cache
    theme.pictures = ()
    layer.grab()
    assert layer._pictures._masters == {} and layer._pictures._cache == {}


@pytest.mark.usefixtures("theme")
def test_widget_closed_while_rendering_raises_nothing(qtbot, monkeypatch):
    from tcalc.ui.widgets.common.picture_layer import PictureLayer

    full = threading.Event()
    record_renders(monkeypatch, hold_full=full)
    window = QWidget()
    window.resize(400, 200)
    layer = PictureLayer(window, WINDOW)
    with qtbot.captureExceptions() as exceptions:
        layer.grab()
        window.close()
        window.deleteLater()
        qtbot.wait(10)
        full.set()
        wait_for_renders(qtbot)
    assert not exceptions


def test_screen_of_another_size_renders_a_new_master(qtbot, monkeypatch, theme):
    picture = theme.pictures[0]
    calls = record_renders(monkeypatch)
    _window, layer = window_layer(qtbot, 400, 200)
    layer.grab()
    qtbot.waitUntil(lambda: len(calls) == 2)
    wait_for_renders(qtbot)
    old_key = layer._pictures._masters[picture][0]
    full = threading.Event()
    monkeypatch.setattr(
        "tcalc.ui.widgets.common.picture_layer.master_size", lambda _p, _s: QSize(2000, 1000)
    )
    record_renders(monkeypatch, hold_full=full)
    layer.grab()
    qtbot.wait(100)  # the new low pass arrives, the full one is held
    assert layer._pictures._masters[picture][0] == old_key  # sharp until the new one
    full.set()
    wait_for_renders(qtbot)
    assert layer._pictures._masters[picture][0] == (2000, 1000)


def test_layer_stays_in_place_while_its_owner_scrolls(qtbot, monkeypatch):
    from tcalc.ui.widgets.common.picture_layer import PictureLayer

    monkeypatch.setattr(
        "tcalc.ui.widgets.common.picture_layer.get_theme", lambda: SimpleNamespace(pictures=())
    )
    lst = QListWidget()
    qtbot.addWidget(lst)
    lst.addItems([str(i) for i in range(100)])
    lst.resize(200, 200)
    layer = PictureLayer(lst.viewport(), HISTORY)
    lst.show()
    lst.verticalScrollBar().setValue(20)
    assert layer.geometry() == lst.viewport().rect()
