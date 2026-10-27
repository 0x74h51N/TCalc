#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QMenu
from shiboken6 import getCppPointer

from tcalc.theme import get_theme, load_theme
from tcalc.ui.config import fonts_config
from tcalc.ui.styles import _build_subs, apply_theme, init_styles


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


class TestKeypadPicture:
    @pytest.fixture(autouse=True)
    def _dark_after(self):
        yield
        load_theme("dark")

    def test_plain_themes_have_none(self):
        load_theme("light")
        assert _build_subs()["keypad_background"] == "none"

    def test_theme_picture_becomes_a_url(self, tmp_path):
        picture = tmp_path / "kitty.png"
        picture.write_bytes(b"")
        load_theme("kitty").keypad_image = picture
        assert _build_subs()["keypad_background"] == f'url("{picture.as_posix()}")'

    def test_missing_picture_is_none(self, tmp_path):
        load_theme("kitty").keypad_image = tmp_path / "missing.png"
        assert _build_subs()["keypad_background"] == "none"
