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

# Non-keypad entries that must not reference the (theme-independent) button families
REMAPPED = {
    ("style", "option_group"): ("checked_base", "hover_base"),
    ("keypad", "custom", "colors"): (
        "spin_bg",
        "spin_text",
        "spin_focus_border",
        "separator",
        "toolbar_separator",
        "add_button_bg",
        "add_button_hover_bg",
    ),
    ("calc", "style", "colors"): ("disabled_bg", "disabled_text"),
    ("calc", "display", "result", "colors"): (
        "frac_bg",
        "frac_bg_hover",
        "frac_bg_pressed",
        "frac_icon",
    ),
    ("calc", "topbar", "memory_colors"): (
        "memory_bg",
        "memory_bg_hover",
        "memory_bg_pressed",
        "memory_disabled_bg",
        "memory_disabled_text",
    ),
}
BUTTON_KEYS = {"accent", "accent_text", "secondary_hover", "secondary_text"}


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


def test_non_keypad_entries_use_theme_following_keys():
    with open(UI_CONFIG, "rb") as f:
        config = tomllib.load(f)
    for path, keys in REMAPPED.items():
        section = config
        for part in path:
            section = section[part]
        for key in keys:
            value = section[key]
            base = value[0] if isinstance(value, list) else value
            assert base not in BUTTON_KEYS, f"{'.'.join(path)}.{key} = {base}"
