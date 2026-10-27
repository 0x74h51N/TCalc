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
from tcalc.theme import ThemeChoice, ThemeMode, custom_themes, load_theme
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


@pytest.mark.parametrize(
    ("choice", "scheme"),
    [
        (ThemeChoice(ThemeMode.LIGHT), Qt.ColorScheme.Light),
        (ThemeChoice(ThemeMode.DARK), Qt.ColorScheme.Dark),
        (ThemeChoice(ThemeMode.SYSTEM), Qt.ColorScheme.Unknown),
        # A custom theme asks for its base theme's scheme
        (ThemeChoice(ThemeMode.CUSTOM, "kitty"), Qt.ColorScheme.Light),
        (ThemeChoice(ThemeMode.CUSTOM, "retro"), Qt.ColorScheme.Dark),
    ],
)
def test_choice_maps_to_qt_scheme(choice, scheme):
    assert choice.scheme == scheme


@pytest.mark.parametrize(
    ("choice", "scheme", "variant"),
    [
        (ThemeChoice(ThemeMode.SYSTEM), Qt.ColorScheme.Light, "light"),
        (ThemeChoice(ThemeMode.SYSTEM), Qt.ColorScheme.Dark, "dark"),
        (ThemeChoice(ThemeMode.SYSTEM), Qt.ColorScheme.Unknown, "dark"),
        (ThemeChoice(ThemeMode.LIGHT), Qt.ColorScheme.Light, "light"),
        (ThemeChoice(ThemeMode.CUSTOM, "kitty"), Qt.ColorScheme.Dark, "kitty"),
    ],
)
def test_choice_picks_theme_variant(choice, scheme, variant):
    assert choice.variant(scheme) == variant


def test_custom_themes_come_from_theme_files():
    assert custom_themes() == {"kitty": "Kitty", "ocean": "Ocean", "retro": "Retro"}


def test_theme_defaults_to_system(tmp_settings):
    assert AppState().theme == ThemeChoice()


def test_theme_persists(tmp_settings):
    AppState().theme = ThemeChoice(ThemeMode.CUSTOM, "ocean")
    assert AppState().theme == ThemeChoice(ThemeMode.CUSTOM, "ocean")


def test_bad_stored_theme_falls_back_to_system(tmp_settings):
    QSettings(tmp_settings, QSettings.Format.IniFormat).setValue("theme", "blue")
    assert AppState().theme == ThemeChoice()


def test_deleted_custom_theme_falls_back_to_system(tmp_settings):
    AppState().theme = ThemeChoice(ThemeMode.CUSTOM, "gone")
    assert AppState().theme == ThemeChoice()


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
