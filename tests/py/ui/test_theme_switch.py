#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import json
import re

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QColor, QFont, QStyleHints
from PySide6.QtWidgets import QApplication, QDockWidget, QMenu, QWidget

import tcalc.app_state as app_state_mod
from tcalc.app_state import get_app_state
from tcalc.theme import ThemeChoice, ThemeMode, get_theme, load_theme
from tcalc.ui.styles import apply_theme, sync_theme
from tcalc.ui.widgets.calc.display.display import Display
from tcalc.ui.widgets.common.button import KeyButton
from tcalc.ui.widgets.common.toaster import Toaster, ToastLevel
from tcalc.ui.widgets.keypad.custom_pad import CustomPad, KSGrid
from tcalc.ui.widgets.keypad.widgets import MainKeypad
from tcalc.ui.widgets.side_panel.side_panel import SidePanel

param = pytest.param

LIGHT_BASE = QColor("#FFFFFF")  # light background_dark


@pytest.fixture
def window(request, qapp, monkeypatch, tmp_path):
    """A MainWindow with isolated settings; the app is back on Dark afterwards. An indirect
    param starts it like a relaunch: {"theme": <variant>, "custom_keys": [<Operation name>]}
    saves one custom pad and applies the theme before the window is built."""
    start = getattr(request, "param", {})
    ini = str(tmp_path / "t.ini")

    def factory(*a, **k):
        return QSettings(ini, QSettings.Format.IniFormat)

    monkeypatch.setattr("tcalc.app_state.QSettings", factory)
    monkeypatch.setattr("tcalc.ui.window.QSettings", factory)
    monkeypatch.setattr("tcalc.ui.layout_presets.QSettings", factory)
    monkeypatch.setattr("tcalc.ui.widgets.keypad.custom_pad.QSettings", factory)
    monkeypatch.setattr("tcalc.ui.widgets.history.history.load_history", lambda: [])
    monkeypatch.setattr("tcalc.ui.widgets.history.history.save_history", lambda _i: None)
    monkeypatch.setattr(app_state_mod, "_app_state", None)
    if keys := start.get("custom_keys"):
        grid = {"max_rows": 6, "keys": [{"operation": op} for op in keys]}
        settings = factory()
        settings.setValue("custom_pads/ids", [0])
        settings.setValue("custom_pad/0/layout", json.dumps({"grids": [grid]}))
        settings.sync()

    from tcalc.ui.window import MainWindow

    old_palette, old_sheet = qapp.palette(), qapp.styleSheet()
    apply_theme(qapp, start.get("theme", "dark"))
    win = MainWindow()
    # The default preset hides custom pads; a saved window state shows them before the window
    for dock in win.findChildren(QDockWidget):
        if isinstance(dock.widget(), CustomPad):
            dock.setVisible(True)
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


# A color written into a widget's own stylesheet does not change with the theme
COLOR_PROPERTY = re.compile(
    r"(^|[{;\s])(color|background(-color)?|border(-(top|right|bottom|left))?|[\w-]+-color)\s*:"
)


def test_widget_stylesheets_set_no_colors(window):
    colored = [
        w.objectName() or type(w).__name__
        for w in window.findChildren(QWidget)
        if COLOR_PROPERTY.search(w.styleSheet())
    ]
    assert colored == []


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


def test_side_panel_fonts_stay_scaled_after_switch(qapp, window, monkeypatch):
    # An app font above the clear button's range (7-10pt)
    monkeypatch.setattr("tcalc.ui.styles._app_font", lambda: QFont(qapp.font().family(), 18))
    apply_theme(qapp, "dark")
    qapp.processEvents()
    assert window.history.clear_button.font().pointSize() <= 10


def test_history_takes_the_theme_monospace_font(qapp, window, _user_themes):
    (_user_themes / "mono").mkdir(parents=True)
    (_user_themes / "mono" / "theme.toml").write_text(
        'name = "Mono"\nbase = "dark"\n[fonts]\nfamily_monospace = "VT323"'
    )
    apply_theme(qapp, "mono")
    assert window.history.list.font().family() == "VT323"


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
        "Retro",
        "Sponge",
        "Add Custom Theme...",
    ]
    assert theme_menu.actions()[3].isSeparator()
    assert not _theme_action(window, "Add Custom Theme...").isEnabled()


def test_theme_added_while_running_shows_when_the_menu_opens(window, _user_themes):
    (_user_themes / "sunset").mkdir(parents=True)
    (_user_themes / "sunset" / "theme.toml").write_text('name = "Sunset"\nbase = "dark"')
    _view_menu(window).actions()[0].menu().aboutToShow.emit()
    assert _theme_action(window, "Sunset").isCheckable()


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


def test_late_scheme_signal_does_not_reapply(window, monkeypatch):
    calls = []
    monkeypatch.setattr("tcalc.ui.styles.apply_theme", lambda app, v: calls.append(v))
    get_app_state().theme = ThemeChoice(ThemeMode.DARK)
    sync_theme(QApplication.instance(), Qt.ColorScheme.Dark)
    assert calls == []


KEY_SETTLE_MS = 100  # lets the window lay out and paint the keys


def _corner_is_background(key: QWidget, inset: int) -> bool:
    """The pixel *inset* px in from the key's top-left corner is not the key's own color."""
    top = key.window()
    image = top.grab().toImage()
    origin = key.mapTo(top, key.rect().topLeft())
    corner = image.pixelColor(origin.x() + inset, origin.y() + inset)
    top_edge = image.pixelColor(origin.x() + key.width() // 2, origin.y() + inset)
    return corner != top_edge


def _square(key: QWidget) -> bool:
    """Qt dropped the key's radius."""
    return not _corner_is_background(key, 2)


def _fully_round(key: QWidget) -> bool:
    """The key's radius is half its short side: a quarter of that in is still outside the arc,
    which a radius below about 85% of it leaves inside the key."""
    return _corner_is_background(key, min(key.width(), key.height()) // 2 // 4)


CUSTOM_KEYS = ["ADD", "SUB", "MUL", "DIV", "POW", "SIN", "COS", "TAN", "LOG", "LN", "MOD"]


@pytest.mark.parametrize(
    "window", [{"theme": "extreme", "custom_keys": CUSTOM_KEYS}], indirect=True
)
@pytest.mark.parametrize("grow", [param(20, id="resized")])
@pytest.mark.parametrize("pad", [MainKeypad, KSGrid])
def test_keys_are_as_round_as_they_fit(qtbot, extreme_theme, window, pad, grow):
    window.resize(window.width() + grow, window.height() + grow)
    qtbot.wait(KEY_SETTLE_MS)
    keys = [k for p in window.findChildren(pad) for k in p.findChildren(KeyButton)]
    keys = [k for k in keys if k.isVisible()]
    assert keys
    assert [k.text() for k in keys if _square(k)] == []
    assert _fully_round(min(keys, key=lambda k: min(k.width(), k.height())))
