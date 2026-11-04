#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import hashlib
import logging

import pytest
from pytest import param

from tcalc.theme import PictureTarget, custom_themes, load_theme
from tcalc.ui.look import DEFAULT_LOOK
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
            "[[keypad]]\nradius = 9\n[fonts]\nsize_default = 11\n",
            lambda t: (t.look.keypad.radius, t.look.fonts.size_default),
            (DEFAULT_LOOK.keypad.radius, 11),
            "theme user.keypad: expected a table, got list",
            id="area array",
        ),
        param(
            '[keypad]\nradius = "9"\n[tooltip]\nradius = 7\n',
            lambda t: (t.look.keypad.radius, t.look.tooltip.radius),
            (DEFAULT_LOOK.keypad.radius, 7),
            "theme user.keypad.radius: expected int, got str",
            id="area wrong type",
        ),
        param(
            "[keypad]\nnope = 3\nradius = 7\n",
            lambda t: (t.look.keypad.radius,),
            (7,),
            "theme user.keypad.nope: unknown key",
            id="area unknown key",
        ),
        param(
            '[tooltip]\nradius = 7\n[keypad]\nradius = "9"\n[result]\nfrac_toggle_radius = 40\n',
            lambda t: (
                t.look.keypad.radius,
                t.look.tooltip.radius,
                t.look.result.frac_toggle_radius,
            ),
            (DEFAULT_LOOK.keypad.radius, 7, 40),
            "theme user.keypad.radius: expected int, got str",
            id="area good, wrong type, good",
        ),
        param(
            '[fonts]\nsize_default = 11\n[[keypad]]\nradius = 9\n[colors]\nprimary = "#ff0000"\n',
            lambda t: (t.look.keypad.radius, t.look.fonts.size_default, t.colors["primary"]),
            (DEFAULT_LOOK.keypad.radius, 11, "#ff0000"),
            "theme user.keypad: expected a table, got list",
            id="good table, array, good table",
        ),
        param(
            "[[fonts]]\nsize_default = 30\n[keypad]\nradius = 7\n",
            lambda t: (t.look.fonts.size_default, t.look.keypad.radius),
            (DEFAULT_LOOK.fonts.size_default, 7),
            "theme user.fonts: expected a table, got list",
            id="fonts array",
        ),
        param(
            '[fonts]\nsize_default = "big"\nfamily_monospace = "VT323"\n',
            lambda t: (t.look.fonts.size_default, t.look.fonts.family_monospace),
            (DEFAULT_LOOK.fonts.size_default, "VT323"),
            "theme user.fonts.size_default: expected int, got str",
            id="fonts wrong type",
        ),
        param(
            '[[colors]]\naccent = "#ff0000"\n[fonts]\nsize_default = 11\n',
            lambda t: (t.colors["accent"], t.look.fonts.size_default),
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
            '[[picker]]\ntext_color = "accent"\n[fonts]\nsize_default = 11\n',
            lambda t: (t.look.picker.text_color, t.look.fonts.size_default),
            (DEFAULT_LOOK.picker.text_color, 11),
            "theme user.picker: expected a table, got list",
            id="color area array",
        ),
        param(
            '[picker]\ntext_color = "nope"\n[icons]\ncolor = "accent"\n',
            lambda t: (t.look.picker.text_color, t.look.icons.color),
            (DEFAULT_LOOK.picker.text_color, "accent"),
            "theme user.picker.text_color: 'nope' is not one of its colors",
            id="missing color",
        ),
        param(
            "[keypad]\nradius = 7\n",
            lambda t: (t.look.keypad.radius, t.look.keypad.min_pt),
            (7, DEFAULT_LOOK.keypad.min_pt),
            "",
            id="one key of an area",
        ),
        param(
            "[keypad.custom]\nspin_font_size = 20\n",
            lambda t: t.look.keypad,
            DEFAULT_LOOK.keypad,
            "theme user.keypad.custom: unknown key",
            id="behavior table",
        ),
        param(
            "[spacing]\nkey_radius = 7\n",
            lambda t: t.look,
            DEFAULT_LOOK,
            "theme user.spacing: unknown key",
            id="old format",
        ),
        param(
            'pictures = "x"\n[fonts]\nsize_default = 11\n',
            lambda t: (t.pictures, t.look.fonts.size_default),
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
    assert {r.getMessage() for r in caplog.records} == ({logged} if logged else set())
    assert load_theme("dark").look == DEFAULT_LOOK


def test_look_override_reaches_stylesheet_and_python(write_theme):
    theme = load_theme(write_theme("[result]\nfrac_toggle_radius = 40\n[keypad]\nradius = 7\n"))
    assert theme.look.result.frac_toggle_radius == 40
    assert theme.look.keypad.radius == 7
    assert "border-radius: 40px" in _build_stylesheet()


# The stylesheet of each bundled theme as master a88c553 built it (2026-11-02): moving the
# values and renaming QSS variables must not change one substituted character. Since
# 2026-11-04 the spin box radius is fixed at 2 px in every theme (#106), and the menu bar's
# preset row rules and the keypad's equals rules, which no widget matched, are gone
@pytest.mark.parametrize(
    "variant, sha256",
    [
        ("light", "4a2dcdfbcce539b04083603391d9ade406ac5a841109a3ef7d1d95e3d52483b2"),
        ("dark", "c59786d571ae1da15babb06fc41f9586291a20e0b8a168bb05c655edcbf4f9d7"),
        ("kitty", "1ffb0ad1ada3f9a808e8911329460a2447cce345acb7de3ce73f53a0d2943502"),
        ("retro", "6b1895c1aacb52ee33fc922d90879cba0b2374cb125ac97602bbc890270a63a5"),
        ("sponge", "4729650c464ea5cb8002d2935af61e81ace4061fee6388a871a50ecdb9aa63e3"),
    ],
)
def test_bundled_themes_style_unchanged(variant, sha256):
    load_theme(variant)
    assert hashlib.sha256(_build_stylesheet().encode()).hexdigest() == sha256
