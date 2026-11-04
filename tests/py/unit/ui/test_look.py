#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import dataclasses
import tomllib
from collections import Counter

import pytest

from tcalc.theme import BUILT_IN_DIR
from tcalc.ui.look import DEFAULT_LOOK, Look, color_places


def test_color_places_are_str():
    for area in dataclasses.fields(Look):
        table = getattr(DEFAULT_LOOK, area.name)
        for f in dataclasses.fields(table):
            if f.name.endswith("_color"):
                assert type(getattr(table, f.name)) is str, f.name


@pytest.mark.parametrize("variant", ["light", "dark"])
def test_builtin_themes_have_every_color_place(variant):
    colors = tomllib.loads((BUILT_IN_DIR / f"{variant}.toml").read_text())["colors"]
    assert [c for c in color_places(DEFAULT_LOOK).values() if c not in colors] == []


def test_qss_names_are_unique():
    names = [
        f"{a.name}_{f.name}"
        for a in dataclasses.fields(Look)
        for f in dataclasses.fields(getattr(DEFAULT_LOOK, a.name))
    ]
    assert [n for n, k in Counter(names).items() if k > 1] == []
