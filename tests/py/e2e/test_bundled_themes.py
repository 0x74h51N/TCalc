#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import logging
import re
import tomllib
from pathlib import Path

import pytest

from tcalc.theme import BUILT_IN_DIR, BUILT_IN_VARIANTS, Theme, _read, load_theme
from tcalc.ui.styles import _build_stylesheet

# The bundled themes on purpose: a bad value here only logs and falls back in the app
_CUSTOM = sorted(p.parent.name for p in BUILT_IN_DIR.glob("*/theme.toml"))
_THEMES = [*BUILT_IN_VARIANTS, *_CUSTOM]
_TEST_THEMES = Path(__file__).parent / "ui" / "themes"


@pytest.fixture(autouse=True)
def _no_user_themes(tmp_path, monkeypatch):
    # A user theme named like a bundled one would replace it
    monkeypatch.setattr("tcalc.theme.user_themes_dir", lambda: tmp_path / "no-user-themes")
    yield
    load_theme("dark")


def _color_names(path: Path) -> set[str]:
    with open(path, "rb") as f:
        return set(tomllib.load(f)["colors"])


@pytest.mark.parametrize("variant", _THEMES)
def test_bundled_theme_loads_with_nothing_skipped(variant, caplog):
    with caplog.at_level(logging.WARNING):
        Theme(variant)
    assert caplog.messages == []


@pytest.mark.parametrize("variant", _THEMES)
def test_bundled_theme_names_only_the_colors_of_dark(variant):
    assert set(Theme(variant).colors) == _color_names(BUILT_IN_DIR / "dark.toml")


@pytest.mark.parametrize("variant", _THEMES)
def test_bundled_theme_pictures_exist(variant):
    missing = [p.file for p in Theme(variant).pictures if not p.file.is_file()]
    assert missing == []


@pytest.mark.parametrize("variant", _THEMES)
def test_bundled_theme_resolves_every_qss_placeholder(variant):
    load_theme(variant)
    leftovers = [line for line in _build_stylesheet().splitlines() if "$" in line]
    assert leftovers == []


def test_theme_template_holds_only_known_keys(monkeypatch, caplog):
    # Every setting in the template is commented out, for the user to uncomment
    text = (BUILT_IN_DIR / "theme-template.toml").read_text(encoding="utf-8")
    settings = re.findall(r"^# ?(\[{1,2}[a-z_.]+\]{1,2}|[a-z_]+\s*=.*)$", text, re.M)
    table = tomllib.loads("\n".join(settings))

    def read(variant: str) -> dict[str, object]:
        return table if variant == "template" else _read(variant)

    monkeypatch.setattr("tcalc.theme._read", read)
    with caplog.at_level(logging.WARNING):
        Theme("template")
    assert caplog.messages == []


@pytest.mark.parametrize("variant", BUILT_IN_VARIANTS)
def test_test_themes_name_the_bundled_colors(variant):
    names = _color_names(_TEST_THEMES / f"{variant}.toml")
    assert names == _color_names(BUILT_IN_DIR / f"{variant}.toml")
