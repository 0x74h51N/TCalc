#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from operator import attrgetter
from typing import Callable

import calc_native
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QColor, QFont, QStyleHints
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDockWidget, QLabel, QRadioButton, QTabBar, QWidget

import tcalc.app_state as app_state_mod
from tcalc.app_state import DockKind, get_app_state
from tcalc.core.ops import Operation
from tcalc.core.parser import tokenize
from tcalc.theme import ThemeChoice, ThemeMode, get_theme, load_theme
from tcalc.ui.controller.menubar.view import ViewOperations
from tcalc.ui.look import DEFAULT_LOOK, ColorName
from tcalc.ui.props import Prop, UiRole
from tcalc.ui.styles import apply_theme
from tcalc.ui.widgets.calc.display.display import Display
from tcalc.ui.widgets.calc.display.result.result import Result
from tcalc.ui.widgets.calc.topbar.topbar import TopBar
from tcalc.ui.widgets.common.button import KeyButton
from tcalc.ui.widgets.common.types import GridLayout, KeyDef, KeySettings, PadLayout
from tcalc.ui.widgets.history.history import History, HistoryItem
from tcalc.ui.widgets.history.storage import HistoryEntry
from tcalc.ui.widgets.keypad.custom_pad import CustomPad, KSGrid, _add_operation
from tcalc.ui.widgets.keypad.widgets import MainKeypad
from tcalc.ui.widgets.side_panel.side_panel import SidePanel

param = pytest.param

LIGHT_BASE = QColor("#FFFFFF")  # the test light's background_dark
LIGHT_SCREEN = QColor("#FEFEFE")  # the test light's screen


@pytest.fixture
def state(qapp, monkeypatch, tmp_path):
    """Isolated settings and app state; the app is back on dark afterwards."""
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
    old_palette, old_font, old_sheet = qapp.palette(), qapp.font(), qapp.styleSheet()
    load_theme("dark")
    yield factory
    load_theme("dark")
    qapp.setPalette(old_palette)
    qapp.setFont(old_font)
    qapp.setStyleSheet(old_sheet)
    qapp.processEvents()


@pytest.fixture
def window(request, qapp, state):
    """A MainWindow on *state*."""
    # An indirect {"theme", "custom_keys"} param starts it like a relaunch with a saved pad
    start = getattr(request, "param", {})
    if keys := start.get("custom_keys"):
        grid = GridLayout(6, tuple(KeySettings(op) for op in keys))
        layout = PadLayout("CustomPad 0", 1, 1, (grid,))
        settings = state()
        settings.setValue("custom_pads/ids", [0])
        settings.setValue("custom_pad/0/layout", json.dumps(dataclasses.asdict(layout)))
        settings.sync()

    from tcalc.ui.window import MainWindow

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
    assert _background(window.findChild(Display)) == LIGHT_SCREEN
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


def test_set_theme_light_requests_qt_scheme_and_persists(state, monkeypatch):
    calls = []
    monkeypatch.setattr(QStyleHints, "setColorScheme", lambda self, s: calls.append(s))
    ViewOperations(None).set_theme(ThemeChoice(ThemeMode.LIGHT))
    assert calls == [Qt.ColorScheme.Light]
    assert get_theme().variant == "light"
    assert get_app_state().theme == ThemeChoice(ThemeMode.LIGHT)


def test_set_theme_custom_restyles_without_a_scheme_change(state, monkeypatch):
    # Extreme and light share Qt's light scheme, so Qt may send no colorSchemeChanged
    monkeypatch.setattr(QStyleHints, "setColorScheme", lambda self, s: None)
    ViewOperations(None).set_theme(ThemeChoice(ThemeMode.CUSTOM, "extreme"))
    assert get_theme().variant == "extreme"
    assert get_app_state().theme == ThemeChoice(ThemeMode.CUSTOM, "extreme")


def _custom_theme_action(window, name: str) -> QAction:
    return next(a for a in window.menubar.view_menu._custom_theme_actions if a.text() == name)


def test_populate_custom_themes_shows_a_theme_added_while_running(window, _user_themes):
    (_user_themes / "sunset").mkdir(parents=True)
    (_user_themes / "sunset" / "theme.toml").write_text('name = "Sunset"\nbase = "dark"')
    window.menubar.view_menu._populate_custom_themes()  # what aboutToShow triggers
    assert _custom_theme_action(window, "Sunset").isCheckable()


def test_populate_custom_themes_checks_the_stored_choice(window):
    get_app_state().theme = ThemeChoice(ThemeMode.CUSTOM, "extreme")
    window.menubar.view_menu._populate_custom_themes()
    assert _custom_theme_action(window, "Extreme").isChecked()


def test_custom_theme_action_sets_the_theme(window, monkeypatch):
    monkeypatch.setattr(QStyleHints, "setColorScheme", lambda self, s: None)
    _custom_theme_action(window, "Extreme").trigger()
    assert get_app_state().theme == ThemeChoice(ThemeMode.CUSTOM, "extreme")


def test_equals_key_paints_the_theme_primary(qapp, window, theme_table):
    apply_theme(qapp, theme_table({"colors": {"primary": "#123456"}}))
    key = next(b for b in window.numpad._buttons.values() if b.text() == "=")
    # Beside the label and past the rounded corner: the key's own face
    pixel = key.grab().toImage().pixelColor(key.width() // 8, key.height() // 2)
    assert pixel.name() == "#123456"


@pytest.mark.parametrize(
    "table",
    [
        param({"colors": {"primary": "#123456", "primary_text": "#FFEE00"}}, id="primary"),
        param(
            {
                "colors": {"mark": "#123456", "mark_text": "#FFEE00"},
                "keypad": {"trig": {"checked": {"color": "mark", "text_color": "mark_text"}}},
            },
            id="trig checked",
        ),
    ],
)
def test_checked_key_paints_primary_with_its_text(qapp, window, theme_table, table):
    apply_theme(qapp, theme_table(table))
    key = next(b for b in window.findChildren(KeyButton) if b.text() == "Shift")
    key.setChecked(True)
    image = key.grab().toImage()
    assert image.pixelColor(key.width() // 8, key.height() // 2).name() == "#123456"
    colors = [image.pixelColor(x, y) for x in range(image.width()) for y in range(image.height())]
    # Antialiased text never reaches the exact color: yellow pixels, not the role's text
    assert any(c.red() > 150 and c.blue() < 64 for c in colors)


def test_pressing_a_checked_key_shows_its_pressed_color(qapp, window):
    apply_theme(qapp, "dark")
    key = next(b for b in window.findChildren(KeyButton) if b.text() == "Shift")
    key.setChecked(True)
    key.setDown(True)
    pixel = key.grab().toImage().pixelColor(key.width() // 8, key.height() // 2)
    assert pixel.name().upper() == get_theme().colors["action_hover"].upper()


def test_side_panel_fonts_stay_scaled_after_switch(qapp, window, monkeypatch):
    # An app font above the clear button's range
    monkeypatch.setattr("tcalc.ui.styles._app_font", lambda: QFont(qapp.font().family(), 18))
    apply_theme(qapp, "dark")
    qapp.processEvents()
    top = DEFAULT_LOOK.history.clear.text.font.max_pt
    assert window.history.clear_button.font().pointSize() <= top


def _history_list(window) -> list[QWidget]:
    return [window.history.list]


def _clear_history(window) -> list[QWidget]:
    return [window.history.clear_button]


def _memory_bar(window) -> list[QWidget]:
    return list(window.memory_bar.font_targets)


def _result_label(window) -> list[QWidget]:
    return [window.findChild(Result).result_label]


def _expression_inputs(window) -> list[QWidget]:
    return window.findChild(Display).editor.expression_inputs()


def _numpad_keys(window) -> list[QWidget]:
    return list(window.numpad._buttons.values())


PINNED = {"font": {"min_pt": 20, "max_pt": 20}}


@dataclass(frozen=True, slots=True)
class FontRangeCase:
    table: dict[str, object]
    widgets: Callable[[QWidget], list[QWidget]]
    top: str  # the range's top in DEFAULT_LOOK


@pytest.mark.parametrize(
    "case",
    [
        param(
            FontRangeCase({"history": {"text": PINNED}}, _history_list, "history.text.font.max_pt"),
            id="history list",
        ),
        param(
            FontRangeCase(
                {"history": {"clear": {"text": PINNED}}},
                _clear_history,
                "history.clear.text.font.max_pt",
            ),
            id="clear history",
        ),
        param(
            FontRangeCase({"memory": {"text": PINNED}}, _memory_bar, "memory.text.font.max_pt"),
            id="memory bar",
        ),
        param(
            FontRangeCase({"result": {"text": PINNED}}, _result_label, "result.text.font.max_pt"),
            id="result",
        ),
        param(
            FontRangeCase(
                {"display": {"expression": {"text": PINNED}}},
                _expression_inputs,
                "display.expression.text.font.max_pt",
            ),
            id="expression",
        ),
        param(
            FontRangeCase(
                {"keypad": {"button": {"text": PINNED}}},
                _numpad_keys,
                "keypad.button.text.font.max_pt",
            ),
            id="keys",
        ),
    ],
)
def test_font_range_follows_the_theme(qapp, window, theme_table, case):
    # The window's first font pass is on a debounce timer: a switch has to come after it to prove
    # anything
    QTest.qWait(300)
    apply_theme(qapp, theme_table(case.table))
    qapp.processEvents()
    assert {w.font().pointSize() for w in case.widgets(window)} == {20}
    apply_theme(qapp, "dark")
    qapp.processEvents()
    top = attrgetter(case.top)(DEFAULT_LOOK)
    assert max(w.font().pointSize() for w in case.widgets(window)) <= top


def test_open_fraction_button_takes_the_theme_padding(qapp, window, theme_table):
    apply_theme(qapp, theme_table({"result": {"fraction": {"padding": {"x": 1}}}}))
    button = window.findChild(Result)._frac_btn
    assert button.iconSize().width() == button.width() - 2


def test_history_takes_the_theme_monospace_font(qapp, window, theme_table):
    apply_theme(qapp, theme_table({"fonts": {"family_monospace": "VT323"}}))
    assert window.history.list.font().family() == "VT323"


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
def test_keys_are_as_round_as_they_fit(qtbot, window, pad, grow):
    window.resize(window.width() + grow, window.height() + grow)
    qtbot.wait(KEY_SETTLE_MS)
    keys = [k for p in window.findChildren(pad) for k in p.findChildren(KeyButton)]
    keys = [k for k in keys if k.isVisible()]
    assert keys
    assert [k.text() for k in keys if _square(k)] == []
    assert _fully_round(min(keys, key=lambda k: min(k.width(), k.height())))


@pytest.fixture
def pinned_key_font(theme_table) -> str:
    return theme_table({"keypad": {"button": {"text": PINNED}}})


@pytest.mark.parametrize("window", [{"theme": "user"}], indirect=True)
def test_keys_keep_their_font_from_launch(qtbot, pinned_key_font, window):
    # The first radius fit writes the keypad's stylesheet, which must not drop the key fonts
    qtbot.wait(KEY_SETTLE_MS)
    assert {key.font().pointSize() for key in _numpad_keys(window)} == {20}


@pytest.fixture
def round_theme(theme_table) -> str:
    """A dark-based theme whose every radius is far above what a widget fits."""
    far = {"radius": 100}
    return theme_table(
        {
            "options": far,
            "history": {"mode": far, "button": far},
            "toast": far,
            "memory": far,
            "result": {"fraction": far},
        }
    )


def _option(window, text: str) -> QWidget:
    return next(b for b in window.findChildren(QRadioButton) if b.text() == text)


def _deg_option(window) -> QWidget:
    return _option(window, "Deg")


def _rad_option(window) -> QWidget:
    return _option(window, "Rad")


def _flat_mode(window) -> QWidget:
    return _option(window, "Flat")


def _math_mode(window) -> QWidget:
    return _option(window, "Math")


def _memory_button(window) -> QWidget:
    return window.findChild(TopBar).get_button("MC")


def _first_keypad_key(window) -> QWidget:
    return window.findChild(MainKeypad).findChildren(KeyButton)[0]


def _history_item(window) -> HistoryItem:
    history = window.findChild(History)
    tokens = tokenize("1+2")
    history.update_history(
        HistoryEntry("1+2", "3", tokens, calc_native.tokens_to_flat_text(tokens.tokens))
    )
    return history.list.itemWidget(history.list.item(0))


def _history_copy_button(window) -> QWidget:
    button = _history_item(window)._copy_btn
    button.show()
    return button


def _fraction_button(window) -> QWidget:
    button = window.findChild(Result)._frac_btn
    button.show()
    return button


def _toast(window) -> QWidget:
    toast = _history_item(window).toaster
    toast.show_toast("Copied")
    return toast


def test_dock_titles_and_tabs_follow_the_theme(qapp, window, theme_table):
    docks = window._docks
    for kind in (DockKind.NUMPAD, DockKind.HISTORY):
        docks[kind].show()
    window.tabifyDockWidget(docks[DockKind.NUMPAD], docks[DockKind.HISTORY])
    qapp.processEvents()
    tabs = next(t for t in window.findChildren(QTabBar) if t.isVisible())
    height = tabs.tabSizeHint(0).height()
    area = {"color": "status_error", "font": {"min_pt": 21}}
    apply_theme(qapp, theme_table({"dock": area, "tabs": area}))
    qapp.processEvents()
    error = get_theme().qcolor(ColorName("status_error"))
    title = docks[DockKind.HISTORY].titleBarWidget().findChild(QLabel)
    assert title.font().pointSize() == 21
    assert title.palette().color(title.foregroundRole()) == error
    assert tabs.tabSizeHint(0).height() > height
    image = tabs.grab().toImage()
    pixels = (image.pixelColor(x, y) for y in range(image.height()) for x in range(image.width()))
    assert any(p == error for p in pixels)


@pytest.mark.parametrize("window", [{"theme": "user"}], indirect=True)
@pytest.mark.parametrize(
    "shown",
    [
        param(_deg_option, id="option group"),
        param(_flat_mode, id="history modes"),
        param(_history_copy_button, id="history item button"),
        param(_fraction_button, id="fraction toggle"),
        param(_toast, id="toast"),
        param(_memory_button, id="memory button"),
    ],
)
def test_a_radius_above_the_widget_is_as_round_as_it_fits(qtbot, round_theme, window, shown):
    widget = shown(window)
    # The default preset hides the history dock and the angle group
    parent = widget
    while parent is not None:
        parent.show()
        parent = parent.parentWidget()
    qtbot.wait(KEY_SETTLE_MS)
    assert widget.isVisible()
    assert not _square(widget)
    assert _fully_round(widget)


@pytest.fixture
def edged_theme(theme_table) -> str:
    """A dark-based theme with a raised edge on every button area."""
    edge = {"edge": {"width": 2, "light_color": "accent_text"}}
    return theme_table(
        {
            "keypad": {"button": edge},
            "memory": edge,
            "options": edge,
            "history": {"mode": edge},
        }
    )


@pytest.mark.parametrize("window", [{"theme": "user"}], indirect=True)
@pytest.mark.parametrize(
    "shown",
    [
        param(_first_keypad_key, id="keypad key"),
        param(_memory_button, id="memory button"),
        param(_rad_option, id="option group"),
        param(_math_mode, id="history modes"),
    ],
)
def test_raised_edge_reaches_every_button_area(qtbot, edged_theme, window, shown):
    widget = shown(window)
    parent = widget
    while parent is not None:
        parent.show()
        parent = parent.parentWidget()
    qtbot.wait(KEY_SETTLE_MS)
    top = widget.window()
    origin = widget.mapTo(top, widget.rect().topLeft())
    edge = top.grab().toImage().pixelColor(origin.x() + widget.width() // 2, origin.y())
    assert edge.name().upper() == get_theme().qcolor(ColorName("accent_text")).name().upper()


def _custom_grid() -> QWidget:
    keys = [KeyDef(label=op.lower(), operation=Operation[op]) for op in CUSTOM_KEYS]
    return KSGrid(0, keys, 6)


def _show_settled(qapp, qtbot, theme: str, pad: QWidget) -> QWidget:
    apply_theme(qapp, theme)
    host = QWidget()
    host.setProperty(Prop.UI_ROLE, UiRole.KEYPAD)
    qtbot.addWidget(host)
    pad.setParent(host)
    pad.resize(400, 400)
    host.show()
    qtbot.wait(KEY_SETTLE_MS)
    return host  # qtbot keeps no reference, so the caller holds the host


@pytest.mark.parametrize("make_pad", [MainKeypad, _custom_grid], ids=["main", "custom"])
def test_keys_stay_round_while_shrinking(qapp, qtbot, window, make_pad):
    # Fully round keys: the radius fitted before a shrink is above half the smaller key
    pad = make_pad()
    _host = _show_settled(qapp, qtbot, "extreme", pad)
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
def test_custom_keys_stay_round_when_the_grid_keeps_its_size(qapp, qtbot, window, change):
    # The keys change size while the grid does not, so no resize refits them
    grid = KSGrid(0, [KeyDef(label="add", operation=Operation.ADD)], 2)
    _host = _show_settled(qapp, qtbot, "extreme", grid)
    change(grid)
    qtbot.wait(KEY_SETTLE_MS)
    assert [k.text() for k in grid.findChildren(KeyButton) if _square(k)] == []
