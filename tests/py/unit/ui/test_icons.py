#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest

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
