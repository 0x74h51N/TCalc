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
import tcalc.ui.widgets.keypad.keypad as keypad_mod
from tcalc.app_state import get_app_state
from tcalc.core.ops import Operation
from tcalc.theme import ThemeChoice, ThemeMode, get_theme, load_theme
from tcalc.ui.styles import apply_theme, sync_theme
from tcalc.ui.widgets.calc.display.display import Display
from tcalc.ui.widgets.common.button import KeyButton
from tcalc.ui.widgets.common.toaster import Toaster, ToastLevel
from tcalc.ui.widgets.common.types import KeyDef
from tcalc.ui.widgets.keypad.custom_pad import CustomPad, KSGrid, _add_operation
from tcalc.ui.widgets.keypad.widgets import MainKeypad
from tcalc.ui.widgets.side_panel.side_panel import SidePanel

param = pytest.param

LIGHT_BASE = QColor("#FFFFFF")  # light background_dark


@pytest.fixture
def window(request, qapp, monkeypatch, tmp_path):
    """A MainWindow with isolated settings; the app is back on Dark afterwards."""
    # An indirect {"theme", "custom_keys"} param starts it like a relaunch with a saved pad
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


KEY_SETTLE_MS = 100  # longer than the keypad's resize debounce


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
    """A radius below about 85% of half the short side leaves this pixel inside the key."""
    return _corner_is_background(key, min(key.width(), key.height()) // 2 // 4)


CUSTOM_KEYS = ["ADD", "SUB", "MUL", "DIV", "POW", "SIN", "COS", "TAN", "LOG", "LN", "MOD"]


@pytest.mark.parametrize(
    "window", [{"theme": "extreme", "custom_keys": CUSTOM_KEYS}], indirect=True
)
@pytest.mark.parametrize("grow", [param(0, id="launch"), param(20, id="resized")])
@pytest.mark.parametrize("pad", [MainKeypad, KSGrid])
def test_keys_are_as_round_as_they_fit(qtbot, extreme_theme, window, pad, grow):
    window.resize(window.width() + grow, window.height() + grow)
    qtbot.wait(KEY_SETTLE_MS)
    keys = [k for p in window.findChildren(pad) for k in p.findChildren(KeyButton)]
    keys = [k for k in keys if k.isVisible()]
    assert keys
    assert [k.text() for k in keys if _square(k)] == []
    assert _fully_round(min(keys, key=lambda k: min(k.width(), k.height())))


@pytest.mark.parametrize("name", ["apply_key_radius", "apply_scaled_fonts"])
def test_main_keypad_restyles_keys_once_per_resize_burst(qapp, qtbot, window, monkeypatch, name):
    keypad = MainKeypad()
    qtbot.addWidget(keypad)
    keypad.resize(300, 300)
    keypad.show()
    qtbot.wait(KEY_SETTLE_MS)
    calls = []
    real = getattr(keypad_mod, name)
    monkeypatch.setattr(keypad_mod, name, lambda *a: calls.append(1) or real(*a))
    for step in range(20):
        keypad.resize(300 + step, 300 + step)
    qtbot.wait(KEY_SETTLE_MS)
    assert len(calls) == 1


def _custom_grid() -> QWidget:
    keys = [KeyDef(label=op.lower(), operation=Operation[op]) for op in CUSTOM_KEYS]
    return KSGrid(0, keys, 6)


def _show_settled(qapp, qtbot, theme: str, pad: QWidget) -> QWidget:
    apply_theme(qapp, theme)
    host = QWidget()
    host.setProperty("uiRole", "keypad")
    qtbot.addWidget(host)
    pad.setParent(host)
    pad.resize(400, 400)
    host.show()
    qtbot.wait(KEY_SETTLE_MS)
    return host  # qtbot keeps no reference, so the caller holds the host


@pytest.mark.parametrize("make_pad", [MainKeypad, _custom_grid], ids=["main", "custom"])
def test_keys_stay_round_while_shrinking(qapp, qtbot, extreme_theme, window, make_pad):
    # Fully round keys: the radius fitted before a shrink is above half the smaller key
    pad = make_pad()
    _host = _show_settled(qapp, qtbot, extreme_theme, pad)
    pad.resize(370, 370)
    qapp.processEvents()
    assert [k.text() for k in pad.findChildren(KeyButton) if _square(k)] == []


def _add_keys(grid: KSGrid) -> None:
    for op in CUSTOM_KEYS:
        _add_operation(grid.keys, Operation[op], grid.max_rows)
    grid.rebuild()


def _start_editing(grid: KSGrid) -> None:
    grid.editing = True


@pytest.mark.parametrize("change", [_add_keys, _start_editing])
def test_custom_keys_stay_round_when_the_grid_keeps_its_size(
    qapp, qtbot, extreme_theme, window, change
):
    # The keys change size while the grid does not, so no resize refits them
    grid = KSGrid(0, [KeyDef(label="add", operation=Operation.ADD)], 2)
    _host = _show_settled(qapp, qtbot, extreme_theme, grid)
    change(grid)
    qtbot.wait(KEY_SETTLE_MS)
    assert [k.text() for k in grid.findChildren(KeyButton) if _square(k)] == []
