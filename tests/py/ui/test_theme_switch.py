#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

import tcalc.app_state as app_state_mod
from tcalc.theme import load_theme
from tcalc.ui.styles import apply_color_scheme
from tcalc.ui.widgets.calc.display.display import Display
from tcalc.ui.widgets.common.toaster import Toaster, ToastLevel
from tcalc.ui.widgets.side_panel.side_panel import SidePanel

LIGHT_BASE = QColor("#FFFFFF")  # light background_dark


@pytest.fixture
def window(qapp, monkeypatch, tmp_path):
    """A MainWindow with isolated settings; the app is back on Dark afterwards."""
    ini = str(tmp_path / "t.ini")

    def factory(*a, **k):
        return QSettings(ini, QSettings.Format.IniFormat)

    monkeypatch.setattr("tcalc.app_state.QSettings", factory)
    monkeypatch.setattr("tcalc.ui.window.QSettings", factory)
    monkeypatch.setattr("tcalc.ui.layout_presets.QSettings", factory)
    monkeypatch.setattr("tcalc.ui.widgets.history.history.load_history", lambda: [])
    monkeypatch.setattr("tcalc.ui.widgets.history.history.save_history", lambda _i: None)
    monkeypatch.setattr(app_state_mod, "_app_state", None)

    from tcalc.ui.window import MainWindow

    old_palette, old_sheet = qapp.palette(), qapp.styleSheet()
    apply_color_scheme(qapp, Qt.ColorScheme.Dark)
    win = MainWindow()
    win.show()
    qapp.processEvents()
    yield win
    win.close()
    win.deleteLater()
    load_theme("dark")
    qapp.setPalette(old_palette)
    qapp.setStyleSheet(old_sheet)
    qapp.processEvents()


def _background(widget: QWidget) -> QColor:
    return widget.palette().color(widget.backgroundRole())


def test_widgets_have_no_color_stylesheets(window):
    styled = [
        w.objectName() or type(w).__name__ for w in window.findChildren(QWidget) if w.styleSheet()
    ]
    assert styled == []


def test_switch_reaches_open_widgets(qapp, window):
    apply_color_scheme(qapp, Qt.ColorScheme.Light)
    assert _background(window.findChild(SidePanel)) == LIGHT_BASE
    assert _background(window.findChild(Display)) == LIGHT_BASE
    assert "$" not in qapp.styleSheet()


def test_switch_reaches_hidden_widgets(qapp, window):
    panel = window.findChild(SidePanel)
    panel.hide()
    apply_color_scheme(qapp, Qt.ColorScheme.Light)
    panel.show()
    qapp.processEvents()
    assert _background(panel) == LIGHT_BASE


def test_keypad_rules_are_scoped(qapp, window):
    selectors = [
        line for line in qapp.styleSheet().splitlines() if "{" in line or line.endswith(",")
    ]
    leaking = [
        s
        for s in selectors
        if ("QPushButton[keypadRole]" in s or 'keypadRole="' in s and '"memory"' not in s)
        and 'QWidget[uiRole="keypad"]' not in s
    ]
    bare = [s for s in selectors if s.split("{")[0].strip().rstrip(",") in ("QSpinBox", "QFrame")]
    assert leaking == [] and bare == []


def test_user_key_colors_survive_switch(qapp, window):
    key = QWidget(window)
    key.setStyleSheet("background: #123456;")
    apply_color_scheme(qapp, Qt.ColorScheme.Light)
    assert key.styleSheet() == "background: #123456;"


def test_toast_is_styled_by_level_not_inline(qapp, window):
    toaster = Toaster(window)
    toaster.show_toast("x", ToastLevel.ERROR)
    assert toaster.styleSheet() == "" and toaster.property("toastLevel") == "error"
