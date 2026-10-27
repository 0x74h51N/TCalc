#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest
from PySide6.QtGui import QColor, QIcon

from tcalc.theme import get_theme, load_theme
from tcalc.ui.manubar import defins
from tcalc.ui.manubar.menu_builder import SubmenuItem
from tcalc.ui.utils import ICONS_DIR, get_icon

BUNDLED = sorted(p.stem for p in ICONS_DIR.glob("*.svg"))


def _menu_icons(items) -> set[str]:
    icons: set[str] = set()
    for item in items:
        if getattr(item, "icon", ""):
            icons.add(item.icon)
        if isinstance(item, SubmenuItem):
            icons |= _menu_icons(item.items)
    return icons


MENU_ICONS = sorted(
    _menu_icons(
        defins.FILE_MENU_ACTIONS
        + defins.EDIT_MENU_ACTIONS
        + defins.VIEW_ACTIONS
        + defins.SETTINGS_ACTIONS
    )
)


@pytest.mark.usefixtures("qapp")
@pytest.mark.parametrize("name", BUNDLED)
def test_bundled_icon_loads(name):
    assert not get_icon(name).isNull()


@pytest.mark.usefixtures("qapp")
@pytest.mark.parametrize("name", MENU_ICONS)
def test_menu_icon_is_bundled(name):
    assert not get_icon(name).isNull()


def test_bundle_is_not_empty():
    assert BUNDLED


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
    assert _opaque_color(get_icon("edit-copy")) == QColor("#232629")


@pytest.mark.usefixtures("qapp")
@pytest.mark.parametrize("variant", ["dark", "light"])
def test_untinted_icons_keep_their_colors(variant):
    load_theme(variant)
    try:
        assert _opaque_color(get_icon("edit-delete")) == QColor("#da4453")
    finally:
        load_theme("dark")


def _same_image(a: QIcon, b: QIcon) -> bool:
    return a.pixmap(32, 32).toImage() == b.pixmap(32, 32).toImage()


@pytest.mark.usefixtures("qapp", "light")
def test_light_variant_file_is_used():
    icon = get_icon("snap-angle-symbolic")
    assert _same_image(icon, QIcon(str(ICONS_DIR / "light" / "snap-angle-symbolic.svg")))
    assert not _same_image(icon, QIcon(str(ICONS_DIR / "snap-angle-symbolic.svg")))


@pytest.mark.usefixtures("qapp")
def test_dark_has_no_variant_dir_and_falls_back():
    load_theme("dark")
    assert not (ICONS_DIR / "dark").exists()
    icon = get_icon("snap-angle-symbolic")
    assert _same_image(icon, QIcon(str(ICONS_DIR / "snap-angle-symbolic.svg")))


@pytest.mark.usefixtures("qapp")
def test_shown_icon_follows_a_switch():
    load_theme("dark")
    icon = get_icon("edit-copy")
    assert _opaque_color(icon) == QColor("#fcfcfc")
    load_theme("light")
    try:
        assert _opaque_color(icon) == QColor("#232629")  # same QIcon, new tint
    finally:
        load_theme("dark")


@pytest.mark.usefixtures("qapp")
def test_angle_icon_switches_file():
    load_theme("dark")
    icon = get_icon("snap-angle-symbolic")
    load_theme("light")
    try:
        assert _same_image(icon, QIcon(str(ICONS_DIR / "light" / "snap-angle-symbolic.svg")))
    finally:
        load_theme("dark")


@pytest.mark.usefixtures("qapp")
def test_red_icon_stays_red_after_switch():
    load_theme("dark")
    icon = get_icon("edit-delete")
    load_theme("light")
    try:
        assert _opaque_color(icon) == QColor("#da4453")
    finally:
        load_theme("dark")


@pytest.mark.usefixtures("qapp")
def test_tint_key_follows_a_switch():
    load_theme("dark")
    icon = get_icon("frac", tint_key="control_accent")
    load_theme("light")
    try:
        assert _opaque_color(icon) == QColor(get_theme().colors["control_accent"])
    finally:
        load_theme("dark")


@pytest.mark.usefixtures("qapp")
def test_kitty_uses_its_base_variant_files():
    load_theme("kitty")
    try:
        icon = get_icon("snap-angle-symbolic")
        assert _same_image(icon, QIcon(str(ICONS_DIR / "light" / "snap-angle-symbolic.svg")))
    finally:
        load_theme("dark")
