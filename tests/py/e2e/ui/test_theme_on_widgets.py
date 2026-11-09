#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Callable

import pytest
from PySide6.QtCore import QPoint, QSettings
from PySide6.QtGui import QAction, QColor, QPalette
from PySide6.QtWidgets import QApplication, QListView, QMenu, QPushButton
from pytest import param
from shiboken6 import getCppPointer

from tcalc.core.ops import Operation
from tcalc.theme import get_theme, load_theme
from tcalc.ui.look import DEFAULT_LOOK, look_fields, qss_name
from tcalc.ui.styles import _build_stylesheet, apply_theme, init_styles
from tcalc.ui.widgets.common.picker import SearchablePicker
from tcalc.ui.widgets.keypad import custom_pad
from tcalc.ui.widgets.keypad.custom_pad import CustomPad
from tests.py.helpers import opaque_color


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
            (QPalette.ColorRole.Highlight, "primary"),
            (QPalette.ColorRole.HighlightedText, "primary_text"),
        ],
    )
    def test_role_follows_theme(self, palette, role, token):
        assert palette.color(role) == QColor(get_theme().colors[token])


def _assert_fixed_font(qapp):
    assert qapp.font().family() == DEFAULT_LOOK.fonts.family_default
    assert qapp.font().pointSize() == DEFAULT_LOOK.fonts.size_default
    menu = QMenu()  # platform themes give menus a font of their own
    assert qapp.font(menu).family() == DEFAULT_LOOK.fonts.family_default


def test_app_font_is_fixed_from_config(styled):
    _assert_fixed_font(styled)


def test_scheme_switch_keeps_style_and_fonts(styled):
    """A switch only re-polishes: replacing the style would reload the platform's fonts."""
    style = getCppPointer(styled.style())
    apply_theme(styled, "light")
    assert getCppPointer(styled.style()) == style
    _assert_fixed_font(styled)


def _menu_font_size(pad: CustomPad) -> int:
    menu = QMenu()
    menu.ensurePolished()
    return menu.font().pixelSize()


def _item_pixel(menu: QMenu, action: QAction) -> str:
    menu.show()
    QApplication.processEvents()
    # Right of the label, inside the item's rounded corners
    rect = menu.actionGeometry(action)
    return menu.grab().toImage().pixelColor(rect.right() - 6, rect.center().y()).name().upper()


def _plain_menu(menu: QMenu) -> tuple[QMenu, QAction]:
    action = menu.addAction("Item")
    menu.addAction("Other")
    return menu, action


def _menu_item_color(pad: CustomPad) -> str:
    menu, action = _plain_menu(QMenu())
    return _item_pixel(menu, action)


def _menu_item_hover(pad: CustomPad) -> str:
    menu, action = _plain_menu(QMenu())
    menu.setActiveAction(action)
    return _item_pixel(menu, action)


def _menu_item_disabled(pad: CustomPad) -> str:
    menu, action = _plain_menu(QMenu())
    action.setEnabled(False)
    return _item_pixel(menu, action)


def _custom_pad_menu_item(pad: CustomPad) -> str:
    menu, action = _plain_menu(pad._styled_menu(pad))
    return _item_pixel(menu, action)


def _add_key(pad: CustomPad) -> QPushButton:
    pad._toggle_edit(True)
    button = pad._grids[0]._add_button
    button.resize(40, 40)
    button.show()
    QApplication.processEvents()
    return button


def _add_key_pressed(pad: CustomPad) -> str:
    button = _add_key(pad)
    button.setDown(True)
    # A corner of the key, away from the icon
    return button.grab().toImage().pixelColor(3, 3).name().upper()


def _add_key_icon_color(pad: CustomPad) -> str:
    return opaque_color(_add_key(pad).icon()).name().upper()


def _top_edge(button: QPushButton) -> str:
    return button.grab().toImage().pixelColor(button.width() // 2, 1).name().upper()


def _add_key_top_edge(pad: CustomPad) -> str:
    return _top_edge(_add_key(pad))


def _add_key_corner(pad: CustomPad) -> str:
    pad._toggle_edit(True)
    pad.resize(320, 360)
    pad.show()
    QApplication.processEvents()
    grid = pad._grids[0]
    grid._fit_key_radius()
    QApplication.processEvents()
    corner = grid._add_button.mapTo(pad, QPoint(2, 2))
    return pad.grab().toImage().pixelColor(corner).name().upper()


def _icon_button(pad: CustomPad) -> QPushButton:
    pad._toggle_edit(True)
    button = pad._grids[0]._edit_btn
    button.resize(40, 40)
    button.show()
    QApplication.processEvents()
    return button


def _icon_button_color(pad: CustomPad) -> str:
    return _icon_button(pad).grab().toImage().pixelColor(5, 5).name().upper()


def _icon_button_top_edge(pad: CustomPad) -> str:
    return _top_edge(_icon_button(pad))


MARK = {"colors": {"mark": "#123456"}}
ITEM = {"menu": {"item": {"color": "mark"}}}
KEY_EDGE = MARK | {"keypad": {"button": {"edge": {"width": 3, "light_color": "mark"}}}}


@dataclass(frozen=True, slots=True)
class ThemeReachCase:
    table: Mapping[str, object]
    shown: Callable[[CustomPad], object]
    expected: int | str


@pytest.mark.parametrize(
    "case",
    [
        param(
            ThemeReachCase(
                {"menu": {"panel": {"text": {"font": {"min_pt": 21}}}}}, _menu_font_size, 21
            ),
            id="menu font size",
        ),
        param(
            ThemeReachCase(MARK | ITEM, _menu_item_color, "#123456"),
            id="menu item color",
        ),
        param(
            ThemeReachCase(
                MARK | {"menu": {"item": {"hover_color": "mark"}}}, _menu_item_hover, "#123456"
            ),
            id="menu item hover color",
        ),
        param(
            ThemeReachCase(
                MARK | {"menu": {"item": {"disabled": {"color": "mark"}}}},
                _menu_item_disabled,
                "#123456",
            ),
            id="menu item disabled color",
        ),
        param(
            ThemeReachCase(
                {"colors": {"mark": "#123456", "own": "#654321"}}
                | ITEM
                | {"custom_pad": {"menu": {"background_color": "own"}}},
                _custom_pad_menu_item,
                "#654321",
            ),
            id="custom pad menu item keeps its own background",
        ),
        param(
            ThemeReachCase(
                MARK | {"custom_pad": {"add_key": {"pressed_color": "mark"}}},
                _add_key_pressed,
                "#123456",
            ),
            id="add key pressed color",
        ),
        param(
            ThemeReachCase(
                MARK | {"custom_pad": {"add_key": {"text": {"color": "mark"}}}},
                _add_key_icon_color,
                "#123456",
            ),
            id="add key icon color",
        ),
        param(
            ThemeReachCase(KEY_EDGE, _add_key_top_edge, "#123456"),
            id="add key edge follows the keys",
        ),
        param(
            ThemeReachCase(
                {"colors": {"mark": "#123456", "background": "#654321"}}
                | {"keypad": {"button": {"radius": 15}}}
                | {"custom_pad": {"add_key": {"color": "mark"}}},
                _add_key_corner,
                "#654321",
            ),
            id="add key radius follows the keys",
        ),
        param(
            ThemeReachCase(
                MARK | {"icon_button": {"color": "mark"}}, _icon_button_color, "#123456"
            ),
            id="icon button color",
        ),
        param(
            ThemeReachCase(
                MARK | {"icon_button": {"edge": {"width": 3, "light_color": "mark"}}},
                _icon_button_top_edge,
                "#123456",
            ),
            id="icon button edge",
        ),
    ],
)
def test_theme_reaches_the_menu_and_the_pad(styled, theme_table, pad, case):
    apply_theme(styled, theme_table(case.table))
    assert case.shown(pad) == case.expected


def test_theme_sets_the_picker_font_size(styled, theme_table):
    apply_theme(styled, theme_table({"picker": {"text": {"font": {"min_pt": 17}}}}))
    picker = SearchablePicker([("sin", None)])
    view = picker.findChild(QListView)
    view.ensurePolished()
    assert view.font().pointSize() == 17


def test_theme_picks_which_color_a_place_uses(styled, theme_table):
    apply_theme(styled, theme_table({"picker": {"text": {"color": "accent_text"}}}))
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


@pytest.mark.usefixtures("styled")
@pytest.mark.parametrize("variant", ["dark", "light", "extreme"])
def test_every_qss_placeholder_resolves(variant):
    load_theme(variant)
    leftovers = [line for line in _build_stylesheet().splitlines() if "$" in line]
    assert leftovers == []


def test_qss_names_are_unique():
    names = [qss_name(f) for f in look_fields(DEFAULT_LOOK)]
    assert [n for n, k in Counter(names).items() if k > 1] == []


def test_light_scheme_sets_light_palette(styled):
    apply_theme(styled, "light")
    assert styled.palette().color(QPalette.ColorRole.Window) == QColor("#F4F5F7")


def test_reapplying_does_not_stack_stylesheet(styled):
    apply_theme(styled, "light")
    n = len(styled.styleSheet())
    apply_theme(styled, "dark")
    apply_theme(styled, "light")
    assert len(styled.styleSheet()) == n


def test_theme_sets_the_monospace_font(theme_table):
    theme = load_theme(theme_table({"fonts": {"family_monospace": "VT323"}}))
    try:
        assert theme.look.fonts.family_monospace == "VT323"
    finally:
        load_theme("dark")
