#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import tomllib
from collections import Counter

import pytest

from tcalc.theme import BUILT_IN_DIR
from tcalc.ui.look import DEFAULT_LOOK, ColorField, look_fields, qss_name


@pytest.mark.parametrize("variant", ["light", "dark"])
def test_builtin_themes_have_every_color_place(variant):
    colors = tomllib.loads((BUILT_IN_DIR / f"{variant}.toml").read_text())["colors"]
    places = [f for f in look_fields(DEFAULT_LOOK) if isinstance(f, ColorField)]
    assert [f.path for f in places if f.color not in colors] == []


def test_qss_names_are_unique():
    names = [qss_name(f) for f in look_fields(DEFAULT_LOOK)]
    assert [n for n, k in Counter(names).items() if k > 1] == []
