#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def _user_themes(tmp_path, monkeypatch):
    """The user's own themes folder, empty, so tests never read the real one."""
    folder = tmp_path / "user-themes"
    monkeypatch.setattr("tcalc.theme.user_themes_dir", lambda: folder)
    return folder


@pytest.fixture
def own_themes(monkeypatch):
    """dark and light are the test files, and extreme is the one custom theme."""
    monkeypatch.setattr("tcalc.theme.BUILT_IN_DIR", Path(__file__).parent / "ui" / "themes")


@pytest.fixture
def theme_table(monkeypatch):
    """Makes the variant "user" answer with a table, and returns its name."""
    from tcalc.theme import _read

    def install(table: dict[str, object], base: str = "dark") -> str:
        def read(variant: str) -> dict[str, object]:
            if variant == "user":
                return {"name": "User", "base": base, **table}
            return _read(variant)

        monkeypatch.setattr("tcalc.theme._read", read)
        return "user"

    return install
