#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from operator import attrgetter
from pathlib import Path

import pytest
from PySide6.QtGui import QColor
from pytest import param

from tcalc.theme import load_theme

# The bundled themes on purpose: contrast on an invented theme tests nothing
_BUNDLED = Path(__file__).parents[4] / "src" / "tcalc" / "themes"
_THEMES = ["dark", "light", *sorted(p.parent.name for p in _BUNDLED.glob("*/theme.toml"))]


@pytest.fixture(autouse=True)
def _bundled_only(tmp_path, monkeypatch):
    # A user theme named like a bundled one would replace it
    monkeypatch.setattr("tcalc.theme.user_themes_dir", lambda: tmp_path / "no-user-themes")
    yield
    load_theme("dark")


def _luminance(value: str) -> float:
    channels = [c / 255 for c in QColor(value).getRgb()[:3]]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("variant", _THEMES)
def test_primary_text_is_readable(variant):
    c = load_theme(variant).colors
    assert _contrast(c["primary_text"], c["primary"]) >= 4.5
    assert _contrast(c["primary_text"], c["primary_hover"]) >= 4.5


@pytest.mark.parametrize("variant", _THEMES)
@pytest.mark.parametrize(
    "place",
    [
        param("memory.text.color", id="memory"),
        param("result.fraction.text.color", id="fraction"),
    ],
)
def test_control_text_is_readable_on_background(variant, place):
    t = load_theme(variant)
    assert _contrast(t.colors[attrgetter(place)(t.look)], t.colors["background"]) >= 4.5
