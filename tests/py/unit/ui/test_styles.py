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
from PySide6.QtCore import Qt
from pytest import param


@dataclass(frozen=True, slots=True)
class QssColorCase:
    value: str
    opacity: float
    expected: str


@pytest.mark.parametrize(
    "case",
    [
        param(QssColorCase("#123456", 1.0, "#123456"), id="opaque"),
        param(QssColorCase("qlineargradient(x)", 1.0, "qlineargradient(x)"), id="gradient"),
        param(QssColorCase("#123456", 0.5, "rgba(18, 52, 86, 50%)"), id="with an opacity"),
    ],
)
def test_qss_color(case):
    from tcalc.ui.styles import qss_color

    assert qss_color(case.value, case.opacity) == case.expected


class FakeApp:
    def __init__(self, calls):
        self._calls = calls

    def setPalette(self, palette):
        self._calls.append(("palette", palette))

    def setFont(self, font):
        self._calls.append(("font", font))

    def setStyleSheet(self, sheet):
        self._calls.append(("sheet", sheet))


def test_apply_theme_applies_each_part_in_order(monkeypatch):
    from tcalc.ui.styles import apply_theme

    calls = []
    monkeypatch.setattr("tcalc.ui.styles.load_theme", lambda v: calls.append(("load", v)))
    monkeypatch.setattr("tcalc.ui.styles._build_palette", lambda: "a palette")
    monkeypatch.setattr("tcalc.ui.styles._app_font", lambda: "a font")
    monkeypatch.setattr("tcalc.ui.styles._build_stylesheet", lambda: "a sheet")
    applied = SimpleNamespace(emit=lambda: calls.append(("applied",)))
    monkeypatch.setattr("tcalc.ui.styles.theme_events", SimpleNamespace(applied=applied))
    apply_theme(FakeApp(calls), "x")
    assert calls == [
        ("load", "x"),
        ("palette", "a palette"),
        ("font", "a font"),
        ("sheet", "a sheet"),
        ("applied",),
    ]


@pytest.mark.parametrize(
    ("current", "applied"),
    [
        param("y", [("app", "x")], id="applies a change"),
        param("x", [], id="nothing when already on"),
    ],
)
def test_sync_theme(monkeypatch, current, applied):
    from tcalc.ui.styles import sync_theme

    choice = SimpleNamespace(variant=lambda _scheme: "x")
    monkeypatch.setattr("tcalc.ui.styles.get_app_state", lambda: SimpleNamespace(theme=choice))
    monkeypatch.setattr("tcalc.ui.styles.get_theme", lambda: SimpleNamespace(variant=current))
    calls = []
    monkeypatch.setattr("tcalc.ui.styles.apply_theme", lambda app, v: calls.append((app, v)))
    sync_theme("app", Qt.ColorScheme.Dark)
    assert calls == applied
