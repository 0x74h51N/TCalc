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
from tcalc.ui.styles import app_fonts, apply_theme
from tcalc.ui.utils import ICONS_DIR


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
        # Right after setColorScheme Qt may still report the old scheme
        (ThemeChoice(ThemeMode.LIGHT), Qt.ColorScheme.Dark, "light"),
        (ThemeChoice(ThemeMode.DARK), Qt.ColorScheme.Light, "dark"),
        (ThemeChoice(ThemeMode.CUSTOM, "kitty"), Qt.ColorScheme.Dark, "kitty"),
    ],
)
def test_choice_picks_theme_variant(choice, scheme, variant):
    assert choice.variant(scheme) == variant


def test_custom_themes_come_from_theme_files():
    assert custom_themes() == {
        "kitty": "Kitty",
        "retro": "Retro",
        "sponge": "Sponge",
    }


@pytest.mark.parametrize(
    "toml",
    [
        'name = "Broken"',
        'name = "Broken"\nbase = "blue"',
        'name = "Broken"\nbase = "dark"\n[fonts',
        'base = "dark"',
        'name = "Broken"\nbase = "dark"\n[[pictures]]\nfile = "a.svg"\ntarget = "roof"',
        'name = "Broken"\nbase = "dark"\n[[pictures]]\nfile = "a.svg"\ntarget = "display"\n'
        'tint = "no_such_color"',
    ],
    ids=["no-base", "bad-base", "bad-toml", "no-name", "bad-target", "bad-tint"],
)
def test_broken_custom_theme_is_skipped(_user_themes, toml):
    for variant, text in (("good", 'name = "Good"\nbase = "light"'), ("broken", toml)):
        (_user_themes / variant).mkdir(parents=True)
        (_user_themes / variant / "theme.toml").write_text(text)
    themes = custom_themes()
    assert themes["good"] == "Good" and "broken" not in themes


def test_user_theme_is_listed_and_replaces_a_bundled_one(_user_themes):
    for variant, name in (("sunset", "Sunset"), ("retro", "My Retro")):
        (_user_themes / variant).mkdir(parents=True)
        (_user_themes / variant / "theme.toml").write_text(f'name = "{name}"\nbase = "dark"')
    assert custom_themes() == {
        "kitty": "Kitty",
        "retro": "My Retro",
        "sponge": "Sponge",
        "sunset": "Sunset",
    }


def test_themes_and_icons_do_not_depend_on_the_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert list(custom_themes()) == ["kitty", "retro", "sponge"]
    assert (ICONS_DIR / "palette.svg").is_file()


def test_theme_sets_the_monospace_font(_user_themes):
    (_user_themes / "mono").mkdir(parents=True)
    (_user_themes / "mono" / "theme.toml").write_text(
        'name = "Mono"\nbase = "dark"\n[fonts]\nfamily_monospace = "VT323"'
    )
    load_theme("mono")
    try:
        assert app_fonts().monospace == "VT323"
    finally:
        load_theme("dark")


def test_theme_defaults_to_system(tmp_settings):
    assert AppState().theme == ThemeChoice()


def test_theme_persists(tmp_settings):
    AppState().theme = ThemeChoice(ThemeMode.CUSTOM, "retro")
    assert AppState().theme == ThemeChoice(ThemeMode.CUSTOM, "retro")


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
