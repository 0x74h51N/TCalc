#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "*.warning=false")


@pytest.fixture(autouse=True)
def _user_themes(tmp_path, monkeypatch):
    """The user's own themes folder, empty, so tests never read the real one."""
    folder = tmp_path / "user-themes"
    monkeypatch.setattr("tcalc.theme.user_themes_dir", lambda: folder)
    return folder


@pytest.fixture
def write_theme(_user_themes):
    """Writes the user theme "user" (name "User", base Dark) with *body*; returns its variant."""

    def write(body: str) -> str:
        folder = _user_themes / "user"
        folder.mkdir(parents=True)
        (folder / "theme.toml").write_text(f'name = "User"\nbase = "dark"\n{body}')
        return "user"

    return write
