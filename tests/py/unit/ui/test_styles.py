#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QListView, QMenu
from shiboken6 import getCppPointer

from tcalc.core.ops import Operation
from tcalc.theme import get_theme, load_theme
from tcalc.ui.config import fonts_config
from tcalc.ui.styles import _build_stylesheet, apply_theme, init_styles
from tcalc.ui.widgets.common.picker import SearchablePicker
from tcalc.ui.widgets.keypad import custom_pad
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


def test_theme_picks_which_color_a_place_uses(styled, monkeypatch):
    monkeypatch.setitem(get_theme().color_usage, "picker_text_color", "accent_text")
    styled.setStyleSheet(_build_stylesheet())
    picker = SearchablePicker([("sin", None)])
    view = picker.findChild(QListView)
    view.ensurePolished()
    text = view.palette().color(QPalette.ColorRole.Text)
    assert text == QColor(get_theme().colors["accent_text"])


def test_custom_pad_picker_items_use_the_picker_text_color(styled, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "tcalc.ui.widgets.keypad.custom_pad.QSettings",
        lambda *_: QSettings(str(tmp_path / "t.ini"), QSettings.Format.IniFormat),
    )
    view = CustomPad(1)._op_picker.findChild(QListView)
    view.ensurePolished()
    text = view.palette().color(QPalette.ColorRole.Text)
    assert text == QColor(get_theme().colors["text_primary"])


@pytest.fixture
def pad(styled, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "tcalc.ui.widgets.keypad.custom_pad.QSettings",
        lambda *_: QSettings(str(tmp_path / "t.ini"), QSettings.Format.IniFormat),
    )
    pad = CustomPad(1)
    grid = pad._grids[0]
    custom_pad._add_operation(grid.keys, Operation.ADD, grid.max_rows)
    grid.rebuild()
    return pad


def _pick_color(pad: CustomPad, value: str) -> None:
    pad._open_color_picker((0, 0), "bg", QPoint(0, 0))
    pad._color_picker.item_selected.emit(value)


def test_key_with_a_theme_color_follows_the_theme(styled, pad):
    _pick_color(pad, "$accent")
    button = pad._grids[0]._buttons[0]
    assert get_theme().colors["accent"] in button.styleSheet()
    apply_theme(styled, "light")
    assert get_theme().colors["accent"] in button.styleSheet()


def test_key_with_a_custom_color_keeps_it(styled, pad):
    _pick_color(pad, "#123456")
    apply_theme(styled, "light")
    assert "#123456" in pad._grids[0]._buttons[0].styleSheet()


def test_color_picker_lists_every_theme_color(styled, pad):
    pad._open_color_picker((0, 0), "bg", QPoint(0, 0))
    values = set(pad._color_picker._data_by_row.values())
    assert {f"${name}" for name in get_theme().colors} <= values


def test_theme_spacing_overrides_config_numbers(styled, monkeypatch):
    monkeypatch.setitem(get_theme().spacing, "btn_radius", 40)
    assert "border-radius: 40px" in _build_stylesheet()
