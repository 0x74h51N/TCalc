#
#
#
# TCalc - Copyright (C) 2026 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import gc

import pytest
from PySide6.QtCore import QSettings

import tcalc.app_state as app_state_mod
from tcalc.theme import load_theme
from tcalc.ui.styles import init_styles
from tests.benchmark.conftest import HISTORY_SCENARIO_COUNTS
from tests.benchmark.expressions import drain_events, make_theme_switch_func

from .conftest import run_benchmark

ROUNDS_THEME = 20
WARMUP_THEME = 2


@pytest.fixture
def main_window(qapp, history_seed, monkeypatch, tmp_path):
    ini = str(tmp_path / "t.ini")

    def factory(*a, **k):
        return QSettings(ini, QSettings.Format.IniFormat)

    monkeypatch.setattr("tcalc.app_state.QSettings", factory)
    monkeypatch.setattr("tcalc.ui.window.QSettings", factory)
    monkeypatch.setattr("tcalc.ui.layout_presets.QSettings", factory)
    monkeypatch.setattr(app_state_mod, "_app_state", None)

    from tcalc.ui.window import MainWindow

    old_style, old_palette, old_font = qapp.style().name(), qapp.palette(), qapp.font()
    init_styles(qapp, "dark")
    win = MainWindow()
    win.show()
    drain_events(qapp)
    yield win
    win.close()
    win.deleteLater()
    load_theme("dark")
    qapp.setStyleSheet("")
    qapp.setStyle(old_style)
    qapp.setPalette(old_palette)
    qapp.setFont(old_font)
    drain_events(qapp)


@pytest.mark.benchmark
@pytest.mark.parametrize("history_seed", list(HISTORY_SCENARIO_COUNTS), indirect=True)
def test_theme_switch_benchmark(qapp, benchmark, history_seed, main_window):
    run_benchmark(
        benchmark,
        make_theme_switch_func(qapp, main_window),
        group="Theme Switch",
        name=history_seed,
        rounds=ROUNDS_THEME,
        warmup_rounds=WARMUP_THEME,
    )
    gc.collect()
