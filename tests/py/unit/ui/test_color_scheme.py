#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QPalette

from tcalc.app_state import AppState
from tcalc.theme import ThemeMode, load_theme
from tcalc.ui.styles import apply_theme


@pytest.fixture
def tmp_settings(tmp_path, monkeypatch):
    ini = str(tmp_path / "tcalc.ini")
    monkeypatch.setattr(
        "tcalc.app_state.QSettings", lambda *_: QSettings(ini, QSettings.Format.IniFormat)
    )
    return ini


@pytest.fixture
def restore(qapp):
    old_palette, old_sheet = qapp.palette(), qapp.styleSheet()
    yield
    load_theme("dark")
    qapp.setPalette(old_palette)
    qapp.setStyleSheet(old_sheet)


def test_mode_maps_to_qt_scheme():
    assert [m.scheme for m in ThemeMode] == [
        Qt.ColorScheme.Light,
        Qt.ColorScheme.Dark,
        Qt.ColorScheme.Unknown,
        Qt.ColorScheme.Light,  # Kitty is a light theme
        Qt.ColorScheme.Dark,  # Ocean is a dark theme
    ]


@pytest.mark.parametrize(
    ("mode", "scheme", "variant"),
    [
        (ThemeMode.SYSTEM, Qt.ColorScheme.Light, "light"),
        (ThemeMode.SYSTEM, Qt.ColorScheme.Dark, "dark"),
        (ThemeMode.SYSTEM, Qt.ColorScheme.Unknown, "dark"),
        (ThemeMode.LIGHT, Qt.ColorScheme.Light, "light"),
        (ThemeMode.KITTY, Qt.ColorScheme.Light, "kitty"),
        (ThemeMode.KITTY, Qt.ColorScheme.Dark, "kitty"),
        (ThemeMode.OCEAN, Qt.ColorScheme.Light, "ocean"),
    ],
)
def test_mode_picks_theme_variant(mode, scheme, variant):
    assert mode.variant(scheme) == variant


def test_theme_mode_defaults_to_system(tmp_settings):
    assert AppState().theme_mode is ThemeMode.SYSTEM


def test_theme_mode_persists(tmp_settings):
    AppState().theme_mode = ThemeMode.LIGHT
    assert AppState().theme_mode is ThemeMode.LIGHT


def test_bad_stored_theme_falls_back_to_system(tmp_settings):
    QSettings(tmp_settings, QSettings.Format.IniFormat).setValue("theme", "blue")
    assert AppState().theme_mode is ThemeMode.SYSTEM


@pytest.mark.usefixtures("restore")
def test_light_scheme_sets_light_palette(qapp):
    apply_theme(qapp, "light")
    assert qapp.palette().color(QPalette.ColorRole.Window) == QColor("#F4F5F7")


@pytest.mark.usefixtures("restore")
def test_reapplying_does_not_stack_stylesheet(qapp):
    apply_theme(qapp, "light")
    n = len(qapp.styleSheet())
    apply_theme(qapp, "dark")
    apply_theme(qapp, "light")
    assert len(qapp.styleSheet()) == n
