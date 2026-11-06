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
from PySide6.QtGui import QColor
from PySide6.QtGui import QIcon
from PySide6.QtGui import QPixmap
from pytest import param


def _filled_icon(color: str) -> QIcon:
    pixmap = QPixmap(8, 8)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


def _color(icon: QIcon) -> QColor:
    return icon.pixmap(8, 8).toImage().pixelColor(4, 4)


@pytest.mark.parametrize(
    ("camel", "expected"),
    [
        param("SpeedOfLight", "Speed Of Light", id="words"),
        param("abc", "abc", id="no capital"),
    ],
)
def test_split_camel(camel, expected):
    from tcalc.ui.utils import split_camel

    assert split_camel(camel) == expected


@pytest.mark.usefixtures("qapp")
def test_apply_tint_paints_the_icon():
    from tcalc.ui.utils import _apply_tint

    assert _color(_apply_tint(_filled_icon("#111111"), "#123456")) == QColor("#123456")


@pytest.mark.usefixtures("qapp")
def test_apply_tint_none_returns_the_icon_as_it_is():
    from tcalc.ui.utils import _apply_tint

    icon = _filled_icon("#111111")
    assert _apply_tint(icon, None) is icon


def test_apply_tint_leaves_a_null_icon():
    from tcalc.ui.utils import _apply_tint

    icon = QIcon()
    assert _apply_tint(icon, "#123456") is icon


def _tint_place(look):
    return look.place


@dataclass(frozen=True, slots=True)
class LoadIconCase:
    name: str
    tint: object
    files: tuple[str, ...]
    path: str
    color: str | None


@pytest.mark.parametrize(
    "case",
    [
        param(
            LoadIconCase("a", None, ("family/a.svg", "a.svg"), "family/a.svg", "#icon"),
            id="family file wins",
        ),
        param(LoadIconCase("a", None, ("a.svg",), "a.svg", "#icon"), id="no family file"),
        param(LoadIconCase("kept", None, ("kept.svg",), "kept.svg", None), id="untinted"),
        param(LoadIconCase("a", _tint_place, ("a.svg",), "a.svg", "#place"), id="tint"),
        param(
            LoadIconCase("kept", _tint_place, ("kept.svg",), "kept.svg", "#place"),
            id="tint beats untinted",
        ),
    ],
)
def test_load_icon(monkeypatch, tmp_path, case):
    from tcalc.ui.utils import _load_icon

    (tmp_path / "family").mkdir()
    for file in case.files:
        (tmp_path / file).touch()
    theme = SimpleNamespace(
        base="family",
        colors={"i": "#icon", "p": "#place"},
        look=SimpleNamespace(place="p", palette=SimpleNamespace(icon_color="i")),
    )
    monkeypatch.setattr("tcalc.ui.utils.get_theme", lambda: theme)
    monkeypatch.setattr("tcalc.ui.utils.ICONS_DIR", tmp_path)
    monkeypatch.setattr(
        "tcalc.ui.utils.CONFIG", SimpleNamespace(icons=SimpleNamespace(untinted=("kept",)))
    )
    monkeypatch.setattr("tcalc.ui.utils.QIcon", lambda path: path)
    monkeypatch.setattr("tcalc.ui.utils._apply_tint", lambda path, color: (path, color))
    assert _load_icon(case.name, case.tint) == (str(tmp_path / case.path), case.color)


def test_get_icon_none_is_a_null_icon(monkeypatch):
    from tcalc.ui.utils import get_icon

    monkeypatch.setattr("tcalc.ui.utils.theme_icon", lambda _build: _filled_icon("#111111"))
    assert get_icon(None).isNull()


def test_get_icon_a_name_loads_that_icon(monkeypatch):
    from tcalc.ui.utils import get_icon

    monkeypatch.setattr("tcalc.ui.utils.theme_icon", lambda build: build())
    monkeypatch.setattr("tcalc.ui.utils._load_icon", lambda name, tint: (name, tint))
    assert get_icon("a", "t") == ("a", "t")


@pytest.mark.usefixtures("qapp")
def test_theme_icon_builds_once_per_theme(monkeypatch):
    from tcalc.ui.utils import theme_icon

    themes = [object()]
    monkeypatch.setattr("tcalc.ui.utils.get_theme", lambda: themes[-1])
    built = []

    def build() -> QIcon:
        built.append(1)
        return _filled_icon("#111111" if len(built) == 1 else "#222222")

    icon = theme_icon(build)
    assert _color(icon) == QColor("#111111")
    _color(icon)
    assert len(built) == 1
    themes.append(object())
    assert _color(icon) == QColor("#222222")
