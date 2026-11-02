#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from pathlib import Path

import pytest
from pytest import param

from tcalc import theme
from tcalc.theme import PictureTarget, custom_themes, load_theme
from tcalc.ui.config import CONFIG, STYLESHEET_TABLES, int_fields
from tcalc.ui.styles import _build_stylesheet

DARK_ACCENT = "#343842"


@pytest.fixture(autouse=True)
def _restore_dark():
    yield
    load_theme("dark")


# (theme body after name and base, the values it gives, the values expected, the logged line):
# the first value is the broken part (it falls back), the second a good part of the same file
@pytest.mark.parametrize(
    "body, values, expected, logged",
    [
        param(
            "[[spacing]]\nkey_radius = 9\n[fonts]\nsize_default = 11\n",
            lambda t: (t.ui.style.key_radius, t.ui.fonts.size_default),
            (CONFIG.style.key_radius, 11),
            "theme user [spacing]: expected a table, got list",
            id="spacing array",
        ),
        param(
            '[spacing]\nkey_radius = "9"\ntooltip_radius = 7\n',
            lambda t: (t.ui.style.key_radius, t.ui.style.tooltip_radius),
            (CONFIG.style.key_radius, 7),
            "theme user [spacing].key_radius: expected int, got str",
            id="spacing wrong type",
        ),
        param(
            "[spacing]\nnope = 3\nkey_radius = 7\n",
            lambda t: (t.ui.style.key_radius,),
            (7,),
            "theme user [spacing].nope: unknown name",
            id="spacing unknown name",
        ),
        param(
            "[[fonts]]\nsize_default = 30\n[spacing]\nkey_radius = 7\n",
            lambda t: (t.ui.fonts.size_default, t.ui.style.key_radius),
            (CONFIG.fonts.size_default, 7),
            "theme user [fonts]: expected a table, got list",
            id="fonts array",
        ),
        param(
            '[fonts]\nsize_default = "big"\nmenu_size = 20\n',
            lambda t: (t.ui.fonts.size_default, t.ui.fonts.menu_size),
            (CONFIG.fonts.size_default, 20),
            "theme user [fonts].size_default: expected int, got str",
            id="fonts wrong type",
        ),
        param(
            '[[colors]]\naccent = "#ff0000"\n[fonts]\nsize_default = 11\n',
            lambda t: (t.colors["accent"], t.ui.fonts.size_default),
            (DARK_ACCENT, 11),
            "theme user [colors]: expected a table, got list",
            id="colors array",
        ),
        param(
            '[colors]\naccent = 5\nprimary = "#ff0000"\n',
            lambda t: (t.colors["accent"], t.colors["primary"]),
            (DARK_ACCENT, "#ff0000"),
            "theme user [colors].accent: expected str, got int",
            id="color value not text",
        ),
        param(
            '[[color_usage]]\npicker_text_color = "accent"\n[fonts]\nsize_default = 11\n',
            lambda t: (t.ui.color_usage.picker_text_color, t.ui.fonts.size_default),
            (CONFIG.color_usage.picker_text_color, 11),
            "theme user [color_usage]: expected a table, got list",
            id="color_usage array",
        ),
        param(
            '[color_usage]\npicker_text_color = "nope"\nicon_color = "accent"\n',
            lambda t: (t.ui.color_usage.picker_text_color, t.ui.color_usage.icon_color),
            (CONFIG.color_usage.picker_text_color, "accent"),
            "theme user [color_usage].picker_text_color: 'nope' is not one of its colors",
            id="color_usage missing color",
        ),
        param(
            'pictures = "x"\n[fonts]\nsize_default = 11\n',
            lambda t: (t.pictures, t.ui.fonts.size_default),
            ((), 11),
            "theme user [[pictures]]: expected a list, got str",
            id="pictures not an array",
        ),
        param(
            '[[pictures]]\nfile = "a.svg"\ntarget = "display"\nfit = "fill"\n'
            '[[pictures]]\nfile = "b.svg"\ntarget = "history"\n',
            lambda t: tuple(p.target for p in t.pictures),
            (PictureTarget.HISTORY,),
            "theme user [[pictures]] #1.fit: expected PictureFit, got str 'fill'",
            id="picture bad fit",
        ),
        param(
            '[[pictures]]\nfile = "a.svg"\ntarget = "display"\ntint = "nope"\n'
            '[[pictures]]\nfile = "b.svg"\ntarget = "history"\ntint = "accent"\n',
            lambda t: tuple(p.target for p in t.pictures),
            (PictureTarget.HISTORY,),
            "theme user [[pictures]] #1.tint: 'nope' is not one of its colors",
            id="picture tint missing",
        ),
    ],
)
def test_broken_part_falls_back(write_theme, caplog, body, values, expected, logged):
    variant = write_theme(body)
    with caplog.at_level(logging.WARNING):
        assert custom_themes()[variant] == "User"
        theme = load_theme(variant)
    assert values(theme) == expected
    assert logged in [r.getMessage() for r in caplog.records]
    assert load_theme("dark").ui == CONFIG


def test_spacing_override_reaches_stylesheet_and_python(write_theme):
    theme = load_theme(write_theme("[spacing]\nfrac_toggle_radius = 40\nkey_radius = 7\n"))
    assert theme.ui.calc.display.result.frac_toggle_radius == 40
    assert theme.ui.style.key_radius == 7
    assert "border-radius: 40px" in _build_stylesheet()


# The stylesheet of each bundled theme as master a88c553 built it (2026-11-02): moving the
# values and renaming QSS variables must not change one substituted character
@pytest.mark.parametrize(
    "variant, sha256",
    [
        ("light", "eb02efff73cf8a0cc3e01d1e2d0b83e4938846bb8052c0c886560464cb9f173a"),
        ("dark", "318439088be3c47faf2ba63568c298edee1c306d9a9fad6a6ff2232bb13e7e46"),
        ("kitty", "77f8643b92fe30af6f1adae24f62a4aa775c452ba38373d28c35a541814e4dc9"),
        ("retro", "c5257825df224bc37f7b3d557d7ad2a433a321e625cddfbe56187d753a0e228e"),
        ("sponge", "9c51fae7ca5662f4ac0637caac7d9ef821259b930be5d07698b43842073cb4f3"),
    ],
)
def test_bundled_themes_style_unchanged(variant, sha256):
    load_theme(variant)
    assert hashlib.sha256(_build_stylesheet().encode()).hexdigest() == sha256


def test_stylesheet_names_are_unique():
    names = [
        row.prefix + name for row in STYLESHEET_TABLES for name in int_fields(row.table(CONFIG))
    ]
    names += int_fields(CONFIG.fonts)
    assert [name for name, n in Counter(names).items() if n > 1] == []


def test_no_stylesheet_table_read_through_config():
    """A theme can override these tables, so a read through CONFIG would miss the theme."""
    src = Path(theme.__file__).parent
    paths = "|".join(re.escape(".".join(row.path)) for row in STYLESHEET_TABLES)
    read = re.compile(rf"\bCONFIG\.(?:{paths})\b")
    offenders = [
        f"{path.relative_to(src)}:{n}"
        for path in sorted(src.rglob("*.py"))
        if path.name != "theme.py"
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if read.search(line)
    ]
    assert offenders == []
