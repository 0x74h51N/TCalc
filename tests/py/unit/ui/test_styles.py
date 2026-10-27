#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QListView, QMenu
from shiboken6 import getCppPointer

from tcalc.theme import get_theme, load_theme
from tcalc.ui.config import fonts_config
from tcalc.ui.styles import _build_stylesheet, apply_theme, init_styles
from tcalc.ui.widgets.common.picker import SearchablePicker
from tcalc.ui.widgets.keypad.custom_pad import CustomPad


@pytest.fixture
def styled(qapp):
    old_palette, old_font = qapp.palette(), qapp.font()
    init_styles(qapp, "dark")
    yield qapp
    load_theme("dark")
    qapp.setPalette(old_palette)
    qapp.setFont(old_font)
    qapp.setStyleSheet("")


class TestAppPalette:
    """The app palette comes from theme tokens, not from the OS color scheme."""

    @pytest.fixture
    def palette(self, styled):
        return styled.palette()

    @pytest.mark.parametrize(
        ("role", "token"),
        [
            (QPalette.ColorRole.Window, "background"),
            (QPalette.ColorRole.WindowText, "text_primary"),
            (QPalette.ColorRole.Base, "background_dark"),
            (QPalette.ColorRole.Text, "text_primary"),
            (QPalette.ColorRole.Button, "background_light"),
            (QPalette.ColorRole.ButtonText, "text_primary"),
            (QPalette.ColorRole.Highlight, "selection_background"),
            (QPalette.ColorRole.HighlightedText, "selection_text"),
        ],
    )
    def test_role_follows_theme(self, palette, role, token):
        assert palette.color(role) == QColor(get_theme().colors[token])


def _assert_fixed_font(qapp):
    assert qapp.font().family() == fonts_config["family_default"]
    assert qapp.font().pointSize() == fonts_config["size_default"]
    menu = QMenu()  # platform themes give menus a font of their own
    assert qapp.font(menu).family() == fonts_config["family_default"]


def test_app_font_is_fixed_from_config(styled):
    _assert_fixed_font(styled)


def test_scheme_switch_keeps_style_and_fonts(styled):
    """A switch only re-polishes: replacing the style would reload the platform's fonts."""
    style = getCppPointer(styled.style())
    apply_theme(styled, "light")
    assert getCppPointer(styled.style()) == style
    _assert_fixed_font(styled)


def test_theme_sets_the_menu_font_size(styled, monkeypatch):
    monkeypatch.setitem(get_theme().fonts, "menu_size", 21)
    styled.setStyleSheet(_build_stylesheet())
    menu = QMenu()
    menu.ensurePolished()
    assert menu.font().pixelSize() == 21


def test_theme_sets_the_picker_font_size(styled, monkeypatch):
    monkeypatch.setitem(get_theme().fonts, "picker_size", 17)
    styled.setStyleSheet(_build_stylesheet())
    picker = SearchablePicker([("sin", None)])
    view = picker.findChild(QListView)
    view.ensurePolished()
    assert view.font().pointSize() == 17


def test_custom_pad_picker_items_use_the_picker_text_color(styled, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "tcalc.ui.widgets.keypad.custom_pad.QSettings",
        lambda *_: QSettings(str(tmp_path / "t.ini"), QSettings.Format.IniFormat),
    )
    view = CustomPad(1)._op_picker.findChild(QListView)
    view.ensurePolished()
    text = view.palette().color(QPalette.ColorRole.Text)
    assert text == QColor(get_theme().colors["text_primary"])


def test_theme_spacing_overrides_config_numbers(styled, monkeypatch):
    monkeypatch.setitem(get_theme().spacing, "btn_radius", 40)
    assert "border-radius: 40px" in _build_stylesheet()
