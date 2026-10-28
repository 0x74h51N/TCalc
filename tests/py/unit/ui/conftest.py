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
