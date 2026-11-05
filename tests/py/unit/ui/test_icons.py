#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest
from PySide6.QtGui import QColor, QIcon

from tcalc.theme import load_theme
from tcalc.ui.icon import Icon
from tcalc.ui.utils import ICONS_DIR, get_icon


def test_icon_names_are_the_bundled_files():
    assert {i.value for i in Icon} == {p.stem for p in ICONS_DIR.glob("*.svg")}


@pytest.mark.usefixtures("qapp")
@pytest.mark.parametrize("icon", list(Icon))
def test_bundled_icon_loads(icon):
    assert not get_icon(icon).isNull()


def _opaque_color(icon: QIcon) -> QColor:
    """Color of the first fully opaque pixel of *icon* at 32px."""
    img = icon.pixmap(32, 32).toImage()
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() == 255:
                return c
    raise AssertionError("icon has no opaque pixel")


@pytest.fixture
def light():
    yield load_theme("light")
    load_theme("dark")


@pytest.mark.usefixtures("qapp", "light")
def test_single_color_icon_is_tinted_with_theme_icon_color():
    assert _opaque_color(get_icon(Icon.EDIT_COPY)) == QColor("#232629")


@pytest.mark.usefixtures("qapp")
@pytest.mark.parametrize("variant", ["dark", "light"])
def test_untinted_icons_keep_their_colors(variant):
    load_theme(variant)
    try:
        assert _opaque_color(get_icon(Icon.EDIT_DELETE)) == QColor("#da4453")
    finally:
        load_theme("dark")


def _same_image(a: QIcon, b: QIcon) -> bool:
    return a.pixmap(32, 32).toImage() == b.pixmap(32, 32).toImage()


@pytest.mark.usefixtures("qapp", "light")
def test_light_variant_file_is_used():
    icon = get_icon(Icon.SNAP_ANGLE_SYMBOLIC)
    assert _same_image(icon, QIcon(str(ICONS_DIR / "light" / "snap-angle-symbolic.svg")))
    assert not _same_image(icon, QIcon(str(ICONS_DIR / "snap-angle-symbolic.svg")))


@pytest.mark.usefixtures("qapp")
def test_dark_has_no_variant_dir_and_falls_back():
    load_theme("dark")
    assert not (ICONS_DIR / "dark").exists()
    icon = get_icon(Icon.SNAP_ANGLE_SYMBOLIC)
    assert _same_image(icon, QIcon(str(ICONS_DIR / "snap-angle-symbolic.svg")))


@pytest.mark.usefixtures("qapp")
def test_shown_icon_follows_a_switch():
    load_theme("dark")
    icon = get_icon(Icon.EDIT_COPY)
    assert _opaque_color(icon) == QColor("#fcfcfc")
    load_theme("light")
    try:
        assert _opaque_color(icon) == QColor("#232629")  # same QIcon, new tint
    finally:
        load_theme("dark")


@pytest.mark.usefixtures("qapp")
def test_angle_icon_switches_file():
    load_theme("dark")
    icon = get_icon(Icon.SNAP_ANGLE_SYMBOLIC)
    load_theme("light")
    try:
        assert _same_image(icon, QIcon(str(ICONS_DIR / "light" / "snap-angle-symbolic.svg")))
    finally:
        load_theme("dark")


@pytest.mark.usefixtures("qapp")
def test_red_icon_stays_red_after_switch():
    load_theme("dark")
    icon = get_icon(Icon.EDIT_DELETE)
    load_theme("light")
    try:
        assert _opaque_color(icon) == QColor("#da4453")
    finally:
        load_theme("dark")


@pytest.mark.usefixtures("qapp")
def test_tint_follows_a_switch():
    load_theme("dark")
    icon = get_icon(Icon.FRAC, lambda look: look.result.fraction.text.color)
    theme = load_theme("light")
    try:
        assert _opaque_color(icon) == theme.qcolor(theme.look.result.fraction.text.color)
    finally:
        load_theme("dark")


@pytest.mark.usefixtures("qapp")
def test_kitty_uses_its_base_variant_files():
    load_theme("kitty")
    try:
        icon = get_icon(Icon.SNAP_ANGLE_SYMBOLIC)
        assert _same_image(icon, QIcon(str(ICONS_DIR / "light" / "snap-angle-symbolic.svg")))
    finally:
        load_theme("dark")
