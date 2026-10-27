#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QColor, QStyleHints
from PySide6.QtWidgets import QMenu, QWidget

import tcalc.app_state as app_state_mod
from tcalc.app_state import get_app_state
from tcalc.theme import ThemeChoice, ThemeMode, get_theme, load_theme
from tcalc.ui.styles import apply_theme
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
    apply_theme(qapp, "dark")
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
    apply_theme(qapp, "light")
    assert _background(window.findChild(SidePanel)) == LIGHT_BASE
    assert _background(window.findChild(Display)) == LIGHT_BASE
    assert "$" not in qapp.styleSheet()


def test_switch_reaches_hidden_widgets(qapp, window):
    panel = window.findChild(SidePanel)
    panel.hide()
    apply_theme(qapp, "light")
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
    apply_theme(qapp, "light")
    assert key.styleSheet() == "background: #123456;"


def test_toast_is_styled_by_level_not_inline(qapp, window):
    toaster = Toaster(window)
    toaster.show_toast("x", ToastLevel.ERROR)
    assert toaster.styleSheet() == "" and toaster.property("toastLevel") == "error"


def _view_menu(window) -> QMenu:
    return next(a.menu() for a in window.menuBar().actions() if a.text() == "View")


def _theme_action(window, text: str) -> QAction:
    theme_menu = _view_menu(window).actions()[0].menu()
    return next(a for a in theme_menu.actions() if a.text() == text)


def test_theme_is_first_in_view_menu(window):
    actions = _view_menu(window).actions()
    assert actions[0].text() == "Theme"
    assert actions[1].isSeparator()
    assert actions[2].text() == "Keypad Preset"


def test_theme_items(window):
    theme_menu = _view_menu(window).actions()[0].menu()
    texts = [a.text() for a in theme_menu.actions() if not a.isSeparator()]
    assert texts == [
        "Light",
        "Dark",
        "System Default",
        "Kitty",
        "Ocean",
        "Retro",
        "Sponge",
        "Add Custom Theme...",
    ]
    assert theme_menu.actions()[3].isSeparator()
    assert not _theme_action(window, "Add Custom Theme...").isEnabled()


def test_stored_choice_is_checked(window):
    assert _theme_action(window, "System Default").isChecked()


def test_choosing_light_requests_qt_scheme_and_persists(window, monkeypatch):
    calls = []
    monkeypatch.setattr(QStyleHints, "setColorScheme", lambda self, s: calls.append(s))
    _theme_action(window, "Light").trigger()
    assert calls == [Qt.ColorScheme.Light]
    assert get_app_state().theme == ThemeChoice(ThemeMode.LIGHT)
    assert _theme_action(window, "Light").isChecked()
    assert not _theme_action(window, "System Default").isChecked()


def test_choosing_kitty_restyles_without_a_scheme_change(window, monkeypatch):
    # Kitty and Light share Qt's Light scheme, so Qt may send no colorSchemeChanged
    monkeypatch.setattr(QStyleHints, "setColorScheme", lambda self, s: None)
    _theme_action(window, "Kitty").trigger()
    assert get_theme().variant == "kitty"
    assert get_app_state().theme == ThemeChoice(ThemeMode.CUSTOM, "kitty")
