#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import logging
import tomllib
from pathlib import Path

import pytest
from PySide6.QtGui import QColor
from pytest import param

from tcalc.theme import BUILT_IN_DIR, get_theme, load_theme
from tcalc.ui.styles import _build_subs

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


@pytest.mark.parametrize("variant", ["light", "kitty", "retro", "sponge"])
def test_sets_have_identical_keys(variant):
    assert load_theme(variant).colors.keys() == load_theme("dark").colors.keys()


@pytest.mark.parametrize(
    ("variant", "base"),
    [("dark", "dark"), ("light", "light"), ("kitty", "light"), ("retro", "light")],
)
def test_base_is_the_light_or_dark_family(variant, base):
    assert load_theme(variant).base == base


def test_new_keys_match_old_dark_values():
    c = load_theme("dark").colors
    assert (c["control"], c["control_hover"]) == (c["accent"], c["secondary_hover"])


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


@pytest.mark.parametrize("variant", ["dark", "light", "kitty", "retro", "sponge"])
def test_bundled_theme_colors_are_opaque(variant):
    # The raw file: the loader would have filtered out what this looks for
    folder = BUILT_IN_DIR / variant
    path = folder / "theme.toml" if folder.is_dir() else BUILT_IN_DIR / f"{variant}.toml"
    colors = tomllib.loads(path.read_text())["colors"]
    for name, value in colors.items():
        if name != "screen" or "gradient" not in value:
            assert QColor(value).isValid() and QColor(value).alpha() == 255, name


@pytest.mark.parametrize(
    "value",
    [
        param("rgba(1, 2, 3, 50%)", id="rgba"),
        param("#80123456", id="argb hex"),
        param("RGBA(1, 2, 3, 50%)", id="rgba in capitals"),
        param("rgb(10, 20, 30)", id="rgb, which QColor cannot read"),
        param("notacolor", id="not a color"),
    ],
)
def test_alpha_in_a_user_theme_takes_the_base_color(write_theme, caplog, value):
    with caplog.at_level(logging.WARNING):
        theme = load_theme(write_theme(f'[colors]\naccent = "{value}"\n'))
    assert theme.colors["accent"] == load_theme("dark").colors["accent"]
    assert {r.getMessage() for r in caplog.records} == {
        f"theme user [colors].accent: {value!r} is not an opaque color"
    }


def test_gradient_screen_reaches_the_stylesheet(write_theme):
    gradient = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #000000, stop:1 #FFFFFF)"
    load_theme(write_theme(f'[colors]\nscreen = "{gradient}"\n'))
    assert _build_subs()["display_background_color"] == gradient


@pytest.mark.parametrize("variant", ["dark", "light", "kitty", "retro", "sponge"])
def test_every_qss_placeholder_resolves(variant):
    from tcalc.ui.styles import _build_stylesheet

    load_theme(variant)
    leftovers = [line for line in _build_stylesheet().splitlines() if "$" in line]
    assert leftovers == []


KEYPAD_FAMILIES = ("secondary", "accent", "action")


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
    assert 15 <= QColor(c["accent_text"]).hue() <= 30


def _luminance(value: str) -> float:
    channels = [c / 255 for c in QColor(value).getRgb()[:3]]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


_THEMES = ["dark", "light", "kitty", "retro", "sponge"]


@pytest.mark.parametrize("variant", _THEMES)
def test_primary_text_is_readable(variant):
    c = load_theme(variant).colors
    assert _contrast(c["primary_text"], c["primary"]) >= 4.5
    assert _contrast(c["primary_text"], c["primary_hover"]) >= 4.5


@pytest.mark.parametrize("variant", _THEMES)
@pytest.mark.parametrize(
    "place",
    [
        param(lambda look: look.memory.text.color, id="memory"),
        param(lambda look: look.result.fraction.text.color, id="fraction"),
    ],
)
def test_control_text_is_readable_on_background(variant, place):
    t = load_theme(variant)
    assert _contrast(t.colors[place(t.look)], t.colors["background"]) >= 4.5


def test_only_primary_moves_the_hovers_and_the_selected_row(write_theme):
    load_theme(write_theme('[colors]\nprimary = "#123456"\n'))
    subs = _build_subs()
    assert subs["options_hover_color"] == "rgba(18, 52, 86, 14%)"
    assert subs["history_selected_color"] == "rgba(18, 52, 86, 24%)"
    load_theme("dark")
    assert _build_subs()["options_hover_color"] == "rgba(166, 199, 255, 14%)"
