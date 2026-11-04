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
    theme = load_theme(write_theme("[toast]\npad_y = 40\n[keypad]\nradius = 7\n"))
    assert theme.look.toast.pad_y == 40
    assert theme.look.keypad.radius == 7
    assert "padding: 40px" in _build_stylesheet()


# The stylesheet of each bundled theme as master a88c553 built it (2026-11-02): moving the
# values and renaming QSS variables must not change one substituted character. Since
# 2026-11-04 the spin box radius is fixed at 2 px in every theme (#106), and the menu bar's
# preset row rules and the keypad's equals rules, which no widget matched, are gone, and the
# history item, Clear History, history mode and option font size rules are added (#197); the
# shared icon button rule is fixed (retro and sponge lose their radius) and the history item
# buttons get their own rules; the option, history button, fraction and toast radii leave the
# stylesheet, since Python fits them to the widget; their raised edge's shadow is a fixed dark
# color, not background_dark (white in light); keys, memory and option buttons get raised
# edge rules that apply only under a theme with an edge width (retro, now a 1995 desktop);
# kitty and sponge set the new option, history and menu sizes and radii; the dock title and
# tab text rules are added, which keep the style's own tab
@pytest.mark.parametrize(
    "variant, sha256",
    [
        ("light", "c8ebcda1474ed6f7b81d7d287f311b94a20faa70a58c125b7800a750ee681ed3"),
        ("dark", "8a0dadab72f1056bf16903de7d07c61c0e209e4188b0223d546a0371dfd3e183"),
        ("kitty", "abdff7148087c040898b9f32c6d4a4b23cefd913c140d86a1d1f2ace894b9e40"),
        ("retro", "18d33aca73ae6e7e705e0737b79c6b667c635af521901eb5734c26216a07e303"),
        ("sponge", "c0403a0b0dcd26fb51f77ee0c662fb3a2e457868abe587ecaa6cb2a57717ed5a"),
    ],
)
def test_bundled_themes_style_unchanged(variant, sha256):
    load_theme(variant)
    assert hashlib.sha256(_build_stylesheet().encode()).hexdigest() == sha256
