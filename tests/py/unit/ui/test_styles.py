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

from tcalc.theme import get_theme
from tcalc.ui.styles import apply_styles


class TestAppPalette:
    """The app palette comes from theme tokens, not from the OS color scheme."""

    @pytest.fixture
    def palette(self, qapp):
        old_palette = qapp.palette()
        apply_styles(qapp)
        yield qapp.palette()
        qapp.setPalette(old_palette)
        qapp.setStyleSheet("")

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


def test_app_font_is_fixed_from_config(qapp):
    old_font = qapp.font()
    apply_styles(qapp)
    try:
        fonts = get_theme().fonts
        assert qapp.font().family() == fonts["family_default"]
        assert qapp.font().pointSize() == fonts["size_default"]
        menu = QMenu()  # platform themes give menus a font of their own
        assert qapp.font(menu).family() == fonts["family_default"]
    finally:
        qapp.setFont(old_font)
        qapp.setStyleSheet("")
