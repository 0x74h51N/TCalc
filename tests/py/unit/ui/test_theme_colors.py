#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from pathlib import Path

import pytest
import tomllib

from tcalc.theme import get_theme, load_theme

UI_CONFIG = Path(__file__).parents[4] / "src" / "tcalc" / "ui" / "config.toml"


@pytest.fixture(autouse=True)
def _restore_dark():
    yield
    load_theme("dark")


def test_default_is_dark_and_unchanged():
    t = load_theme("dark")
    assert t.variant == "dark"
    assert t.colors["background"] == "#1E1E1E" and t.colors["accent"] == "#343842"


def test_light_loads_only_light():
    t = load_theme("light")
    assert t.variant == "light" and get_theme() is t
    assert t.colors["background"] == "#F4F5F7"
    assert t.colors["primary"] == load_theme("dark").colors["primary"]  # button family kept


def test_sets_have_identical_keys():
    assert load_theme("light").colors.keys() == load_theme("dark").colors.keys()


def test_new_keys_match_old_dark_values():
    c = load_theme("dark").colors
    assert (c["control"], c["control_hover"], c["control_accent"]) == (
        c["accent"],
        c["secondary_hover"],
        c["accent_text"],
    )


def _values(table):
    for value in table.values():
        if isinstance(value, dict):
            yield from _values(value)
        else:
            yield value


def test_no_alpha_pairs_left_in_ui_config():
    with open(UI_CONFIG, "rb") as f:
        config = tomllib.load(f)
    pairs = [
        v
        for v in _values(config)
        if isinstance(v, list) and len(v) == 2 and isinstance(v[1], float)
    ]
    assert pairs == []


def test_alpha_helper_is_gone():
    import tcalc.ui.utils

    assert not hasattr(tcalc.ui.utils, "rgba")


def test_dark_alpha_values_match_old_look():
    c = load_theme("dark").colors
    assert c["control_bg"] == "rgba(52, 56, 66, 20%)"
    assert c["toast_error_bg"] == "rgba(217, 64, 64, 55%)"


@pytest.mark.usefixtures("qapp")
@pytest.mark.parametrize("variant", ["dark", "light"])
def test_every_qss_placeholder_resolves(variant):
    from PySide6.QtWidgets import QListWidget, QMenuBar, QWidget

    from tcalc.ui.manubar.style import apply_menu_styles
    from tcalc.ui.styles import _load_common_qss
    from tcalc.ui.widgets.calc.display.result.style import apply_style
    from tcalc.ui.widgets.calc.display.style import apply_display_style
    from tcalc.ui.widgets.calc.topbar.style import apply_topbar_style
    from tcalc.ui.widgets.history.style import apply_history_style
    from tcalc.ui.widgets.keypad.style import apply_keypad_style

    load_theme(variant)
    sheets = [_load_common_qss()]
    menubar, history = QMenuBar(), QListWidget()
    apply_menu_styles(menubar)
    apply_history_style(history)
    sheets += [menubar.styleSheet(), history.styleSheet()]
    for apply in (apply_style, apply_display_style, apply_topbar_style, apply_keypad_style):
        w = QWidget()
        apply(w)
        sheets.append(w.styleSheet())
    leftovers = [line for sheet in sheets for line in sheet.splitlines() if "$" in line]
    assert leftovers == []
