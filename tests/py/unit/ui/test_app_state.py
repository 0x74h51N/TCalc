#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pytest
from PySide6.QtCore import QSettings

from tcalc.app_state import AppState


class FakeMode(Enum):
    SYSTEM = "system"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class FakeChoice:
    mode: FakeMode = FakeMode.SYSTEM
    custom: str = ""


@pytest.fixture
def tmp_settings(tmp_path, monkeypatch):
    ini = str(tmp_path / "tcalc.ini")
    monkeypatch.setattr(
        "tcalc.app_state.QSettings", lambda *_: QSettings(ini, QSettings.Format.IniFormat)
    )
    monkeypatch.setattr("tcalc.app_state.ThemeMode", FakeMode)
    monkeypatch.setattr("tcalc.app_state.ThemeChoice", FakeChoice)
    monkeypatch.setattr("tcalc.app_state.custom_themes", lambda: {"mine": "Mine"})
    return ini


def test_theme_defaults_to_system(tmp_settings):
    assert AppState().theme == FakeChoice()


def test_theme_persists(tmp_settings):
    AppState().theme = FakeChoice(FakeMode.CUSTOM, "mine")
    assert AppState().theme == FakeChoice(FakeMode.CUSTOM, "mine")


def test_bad_stored_theme_falls_back_to_system(tmp_settings):
    QSettings(tmp_settings, QSettings.Format.IniFormat).setValue("theme", "blue")
    assert AppState().theme == FakeChoice()


def test_deleted_custom_theme_falls_back_to_system(tmp_settings):
    AppState().theme = FakeChoice(FakeMode.CUSTOM, "gone")
    assert AppState().theme == FakeChoice()
