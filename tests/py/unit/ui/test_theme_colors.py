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
from PySide6.QtGui import QColor

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


@pytest.mark.parametrize("variant", ["light", "kitty", "ocean", "retro", "sponge"])
def test_sets_have_identical_keys(variant):
    assert load_theme(variant).colors.keys() == load_theme("dark").colors.keys()


@pytest.mark.parametrize(
    ("variant", "base"),
    [("dark", "dark"), ("light", "light"), ("kitty", "light"), ("ocean", "dark")],
)
def test_base_is_the_light_or_dark_family(variant, base):
    assert load_theme(variant).base == base


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


@pytest.mark.parametrize("variant", ["dark", "light", "kitty", "ocean", "retro", "sponge"])
def test_every_qss_placeholder_resolves(variant):
    from tcalc.ui.styles import _build_stylesheet

    load_theme(variant)
    leftovers = [line for line in _build_stylesheet().splitlines() if "$" in line]
    assert leftovers == []


KEYPAD_FAMILIES = ("primary", "secondary", "accent", "action")


def test_light_keypad_colors_are_light():
    light, dark = load_theme("light").colors, load_theme("dark").colors
    for family in KEYPAD_FAMILIES:
        for key in (family, f"{family}_hover", f"{family}_text"):
            assert light[key] != dark[key], key
    assert QColor(light["secondary"]).lightness() > QColor(dark["secondary"]).lightness()


def test_only_keypad_qss_uses_keypad_colors():
    ui = UI_CONFIG.parent
    offenders = [
        f"{path.relative_to(ui)}:{n}"
        for path in ui.rglob("*.qss")
        if path.parent.name != "keypad"
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if any(f"${family}" in line for family in KEYPAD_FAMILIES)
    ]
    assert offenders == []


def test_light_accent_is_orange():
    c = load_theme("light").colors
    for key in ("accent_text", "control_accent"):
        assert 15 <= QColor(c[key]).hue() <= 30, key
