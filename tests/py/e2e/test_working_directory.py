#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from tcalc.theme import custom_themes
from tcalc.ui.utils import ICONS_DIR


def test_themes_and_icons_do_not_depend_on_the_working_directory(tmp_path, monkeypatch):
    monkeypatch.setattr("tcalc.theme.user_themes_dir", lambda: tmp_path / "no-user-themes")
    monkeypatch.chdir(tmp_path)
    assert custom_themes()
    assert (ICONS_DIR / "palette.svg").is_file()
