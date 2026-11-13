#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import calc_native
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget
from pytest import param

from tcalc.app_state import RenderMode, get_app_state
from tcalc.core.parser import tokenize
from tcalc.theme import get_theme, load_theme
from tcalc.ui.config import CONFIG
from tcalc.ui.styles import apply_theme
from tcalc.ui.widgets.common.button import OptionGroup
from tcalc.ui.widgets.history.history import History, HistoryItem
from tcalc.ui.widgets.history.storage import HistoryEntry
from tcalc.ui.widgets.history.utils import wrap_expression
from tests.py.helpers import opaque_color


@pytest.fixture
def history(qapp, monkeypatch):
    """Fresh History widget with storage disabled."""
    monkeypatch.setattr("tcalc.ui.widgets.history.history.load_history", lambda: [])
    monkeypatch.setattr("tcalc.ui.widgets.history.history.save_history", lambda _items: None)
    monkeypatch.setattr("tcalc.ui.widgets.history.history.clear_history_file", lambda: None)

    state = get_app_state()
    state._history_mode = RenderMode.FLAT

    widget = History()
    widget.resize(400, 600)
    widget.show()
    qapp.processEvents()

    yield widget

    widget.close()
    widget.deleteLater()
    qapp.processEvents()


@pytest.fixture
def themed(qapp):
    """The app stylesheet, which paints the history rows; the app is back as it was afterwards."""
    old_palette, old_sheet = qapp.palette(), qapp.styleSheet()
    apply_theme(qapp, "dark")
    qapp.processEvents()
    yield
    load_theme("dark")
    qapp.setPalette(old_palette)
    qapp.setStyleSheet(old_sheet)
    qapp.processEvents()


def _add(history: History, expr: str, result: str, qapp) -> None:
    tokens = tokenize(expr)
    flat_text = calc_native.tokens_to_flat_text(tokens.tokens)
    entry = HistoryEntry(expr, result, tokens, flat_text)
    history.update_history(entry)
    qapp.processEvents()


def _expr_text(history: History, row: int) -> str:
    return history._item_widgets[row].expression_label.text()


def _result_text(history: History, row: int) -> str:
    return history.get_result_labels()[row].text()


def _item_widget(history: History, row: int) -> HistoryItem:
    widget = history.list.itemWidget(history.list.item(row))
    assert isinstance(widget, HistoryItem)
    return widget


class TestModeSwitch:
    """Mode radio buttons switch rendering between flat and raw."""

    def test_initial_state(self, history):
        buttons = history._history_modes.buttons()
        assert get_app_state().history_mode == RenderMode.FLAT
        assert buttons[RenderMode.FLAT].isChecked()
        assert buttons[RenderMode.MATH].isEnabled()
        assert buttons[RenderMode.RAW].isEnabled()

    @pytest.mark.parametrize(
        "expr, result",
        [
            ("1+2", "3"),
            ("\\frac{3}{4}+2^{3}", "8.75"),
        ],
        ids=["simple", "mixed-latex"],
    )
    def test_raw_shows_original_expression(self, history, qapp, expr, result):
        _add(history, expr, result, qapp)

        history.set_mode(RenderMode.RAW)
        qapp.processEvents()

        assert _expr_text(history, 0) == expr

    @pytest.mark.parametrize(
        "expr, result",
        [
            ("1+2", "3"),
            ("\\frac{3}{4}+2^{3}", "8.75"),
        ],
        ids=["simple", "mixed-latex"],
    )
    def test_flat_strips_latex(self, history, qapp, expr, result):
        _add(history, expr, result, qapp)

        history.set_mode(RenderMode.FLAT)
        qapp.processEvents()

        text = _expr_text(history, 0)
        assert "\\" not in text

    def test_flat_matches_native_flat_text(self, history, qapp):
        expr = "\\frac{3}{4}+2^{3}"
        _add(history, expr, "8.75", qapp)

        history.set_mode(RenderMode.FLAT)
        qapp.processEvents()

        tokens = tokenize(expr)
        expected = calc_native.tokens_to_flat_text(tokens.tokens)
        assert expected in _expr_text(history, 0)

    def test_mode_round_trip_preserves_items(self, history, qapp):
        _add(history, "1+2", "3", qapp)
        _add(history, "\\frac{3}{4}+2^{3}", "8.75", qapp)

        history.set_mode(RenderMode.RAW)
        qapp.processEvents()
        history.set_mode(RenderMode.FLAT)
        qapp.processEvents()
        history.set_mode(RenderMode.RAW)
        qapp.processEvents()
        history.set_mode(RenderMode.FLAT)
        qapp.processEvents()

        assert history.list.count() == 2
        assert _result_text(history, 0) == "3"
        assert _result_text(history, 1) == "8.75"
        assert "\\" not in _expr_text(history, 1)

    def test_radio_click_triggers_mode_change(self, history, qapp):
        _add(history, "1+2", "3", qapp)

        raw_btn = history._history_modes.buttons()[RenderMode.RAW]
        raw_btn.setChecked(True)
        qapp.processEvents()

        assert get_app_state().history_mode == RenderMode.RAW
        assert _expr_text(history, 0) == "1+2"


class TestListOperations:
    """Add, remove, clear and signal behaviour."""

    def test_empty_on_init(self, history):
        assert history.list.count() == 0

    def test_add_and_remove(self, history, qapp):
        _add(history, "1+1", "2", qapp)
        _add(history, "2+2", "4", qapp)
        _add(history, "3+3", "6", qapp)

        assert history.list.count() == 3
        assert len(history._item_widgets) == 3

        history._remove_item(history.list.item(1))
        qapp.processEvents()

        assert history.list.count() == 2
        assert _result_text(history, 0) == "2"
        assert _result_text(history, 1) == "6"

    def test_clear_removes_all(self, history, qapp):
        _add(history, "1+1", "2", qapp)
        _add(history, "2+2", "4", qapp)

        history.clear_history()
        qapp.processEvents()

        assert history.list.count() == 0
        assert len(history._item_widgets) == 0
        assert len(history.get_result_labels()) == 0

    def test_user_data_stores_raw_expression(self, history, qapp):
        _add(history, "\\frac{1}{2}+1", "1.5", qapp)

        item = history.list.item(0)
        assert item.data(Qt.ItemDataRole.UserRole) == "\\frac{1}{2}+1"

    def test_items_changed_signal_on_add(self, history, qapp):
        received = []
        history.items_changed.connect(lambda: received.append(True))

        _add(history, "1+1", "2", qapp)

        assert len(received) >= 1


class TestHistoryItemWidget:
    """Layout properties of a single HistoryItem."""

    def test_widget_properties(self, history, qapp):
        _add(history, "1+2", "3", qapp)

        w = _item_widget(history, 0)
        assert isinstance(w, HistoryItem)
        assert w.expression_label.alignment() & Qt.AlignmentFlag.AlignRight
        assert w.result_label.alignment() & Qt.AlignmentFlag.AlignRight
        assert w.minimumHeight() >= CONFIG.history.style.item_min_height

    def test_action_buttons_toggle(self, history, qapp):
        _add(history, "1+2", "3", qapp)

        w = _item_widget(history, 0)
        assert not w._copy_btn.isVisible()
        assert not w._remove_btn.isVisible()

        w.show_actions()
        qapp.processEvents()
        assert w._copy_btn.isVisible()
        assert w._remove_btn.isVisible()

        w.hide_actions()
        qapp.processEvents()
        assert not w._copy_btn.isVisible()
        assert not w._remove_btn.isVisible()

    def test_size_hint_min_height(self, history, qapp):
        _add(history, "1+2", "3", qapp)

        item = history.list.item(0)
        assert item.sizeHint().height() >= CONFIG.history.style.item_min_height

    def test_long_expression_taller_than_short(self, history, qapp):
        _add(history, "1+2", "3", qapp)
        _add(history, "1+2+3+4+5+6+7+8+9+10+11+12+13+14+15+16", "136", qapp)

        short_h = _item_widget(history, 0).heightForWidth(200)
        long_h = _item_widget(history, 1).heightForWidth(200)
        assert long_h >= short_h

    def test_math_expression_shows_the_row_color(self, history, qapp, themed):
        # Long enough that the horizontal scrollbar shows, as in issue #97
        _add(history, "+".join(f"\\frac{{{i}}}{{{i + 1}}}" for i in range(1, 20)), "x", qapp)
        history.set_mode(RenderMode.MATH)
        qapp.processEvents()

        w = _item_widget(history, 0)
        viewport = w._expr_scroll.viewport()
        assert w._expr_scroll.horizontalScrollBar().isVisible()
        image = qapp.primaryScreen().grabWindow(history.winId()).toImage()
        inside = viewport.mapTo(history, QPoint(1, 1))
        row_margin = w.mapTo(history, QPoint(1, w._expr_scroll.y() + 1))
        assert image.pixelColor(inside) == image.pixelColor(row_margin)


# ===================================================================
# Theme
# ===================================================================


@pytest.fixture
def apply_user_theme(qapp, theme_table):
    """Applies a theme with *table* on *base*; the app is dark afterwards."""
    old_palette, old_sheet = qapp.palette(), qapp.styleSheet()

    def apply(table: dict[str, object], base: str = "dark") -> None:
        apply_theme(qapp, theme_table(table, base))
        qapp.processEvents()

    yield apply
    load_theme("dark")
    qapp.setPalette(old_palette)
    qapp.setStyleSheet(old_sheet)
    qapp.processEvents()


def _text_color(widget: QWidget) -> str:
    widget.ensurePolished()
    return widget.palette().color(QPalette.ColorRole.WindowText).name().upper()


def _pixel(button: QWidget, x: int, y: int) -> str:
    """Color at (*x*, *y*) of *button* as its item draws it; a button's own grab skips the corners."""
    button.show()
    QApplication.processEvents()
    pos = button.pos()
    return (
        button.parentWidget().grab().toImage().pixelColor(pos.x() + x, pos.y() + y).name().upper()
    )


def _polished(widget: QWidget) -> QWidget:
    widget.ensurePolished()
    return widget


def _mode_button(history: History, mode: RenderMode) -> QWidget:
    return history._history_modes._buttons[mode]


def _expression_color(history: History) -> str:
    return _text_color(_item_widget(history, 0).expression_label)


def _result_color(history: History) -> str:
    return _text_color(_item_widget(history, 0).result_label)


def _result_font_size(history: History) -> int:
    return _item_widget(history, 0).result_label.font().pointSize()


def _copy_icon_color(history: History) -> str:
    return opaque_color(_item_widget(history, 0)._copy_btn.icon()).name().upper()


def _delete_icon_color(history: History) -> str:
    return opaque_color(_item_widget(history, 0)._remove_btn.icon()).name().upper()


def _copy_face(history: History) -> str:
    return _pixel(_item_widget(history, 0)._copy_btn, 2, 11)


def _delete_face(history: History) -> str:
    return _pixel(_item_widget(history, 0)._remove_btn, 2, 11)


def _copy_top_edge(history: History) -> str:
    return _pixel(_item_widget(history, 0)._copy_btn, 11, 0)


def _copy_bottom_edge(history: History) -> str:
    return _pixel(_item_widget(history, 0)._copy_btn, 11, 21)


def _copy_corner_is_the_face(history: History) -> bool:
    corner = _pixel(_item_widget(history, 0)._copy_btn, 2, 2)
    return corner == get_theme().colors["accent_text"].upper()


def _copy_pressed_face(history: History) -> str:
    button = _item_widget(history, 0)._copy_btn
    button.setDown(True)
    return _pixel(button, 2, 11)


def _clear_pressed_face(history: History) -> str:
    history.clear_button.setDown(True)
    # Above the icon and the label
    return _pixel(history.clear_button, history.clear_button.width() // 2, 3)


def _mode_pressed_face(history: History) -> str:
    button = _mode_button(history, RenderMode.MATH)
    button.setDown(True)
    return _pixel(button, 2, button.height() // 2)


def _option(history: History) -> QWidget:
    # The second one: the checked one draws its checked color
    group = OptionGroup([(1, "A"), (2, "B")], 1, lambda look: look.options, history)
    group.show()
    return _polished(group._buttons[2])


def _option_face(history: History) -> str:
    button = _option(history)
    return _pixel(button, 2, button.height() // 2)


def _option_pressed_face(history: History) -> str:
    button = _option(history)
    button.setDown(True)
    return _pixel(button, 2, button.height() // 2)


def _mode_face(history: History) -> str:
    button = _mode_button(history, RenderMode.MATH)
    return _pixel(button, 2, button.height() // 2)


def _option_face_is_sunset(history: History) -> bool:
    return _option_face(history) == "#FF8800"


def _clear_color(history: History) -> str:
    return _text_color(history.clear_button)


def _math_mode_color(history: History) -> str:
    return _text_color(_mode_button(history, RenderMode.MATH))


def _math_mode_font_size(history: History) -> int:
    return _mode_button(history, RenderMode.MATH).font().pointSize()


def _option_font_size(history: History) -> int:
    group = OptionGroup([(1, "A")], 1, lambda look: look.options, history)
    return _polished(group._buttons[1]).font().pointSize()


@dataclass(frozen=True, slots=True)
class HistoryThemeCase:
    table: dict[str, object]
    shown: Callable[[History], object]
    expected: str | int | bool  # a str names a color of the theme


ACCENT = {"color": "accent_text"}
OPTION_FONT = {"options": {"text": {"font": {"min_pt": 15}}}}


@pytest.mark.parametrize(
    "case",
    [
        param(
            HistoryThemeCase({"history": {"expression": ACCENT}}, _expression_color, "accent_text"),
            id="expression color",
        ),
        param(
            HistoryThemeCase({"history": {"result": ACCENT}}, _result_color, "accent_text"),
            id="result color",
        ),
        param(
            HistoryThemeCase(
                {"history": {"result": {"font": {"min_pt": 20, "max_pt": 20}}}},
                _result_font_size,
                20,
            ),
            id="result font range",
        ),
        param(
            HistoryThemeCase(
                {"history": {"copy": {"text": {"color": "status_error"}}}},
                _copy_icon_color,
                "status_error",
            ),
            id="copy icon color",
        ),
        param(
            HistoryThemeCase(
                {"history": {"delete": {"text": ACCENT}}}, _delete_icon_color, "accent_text"
            ),
            id="delete icon color",
        ),
        param(
            HistoryThemeCase({"history": {"copy": ACCENT}}, _copy_face, "accent_text"),
            id="copy button color",
        ),
        param(
            HistoryThemeCase({"history": {"delete": ACCENT}}, _delete_face, "accent_text"),
            id="delete button color",
        ),
        param(
            HistoryThemeCase(
                {"history": {"copy": {"pressed_color": "accent_text"}}},
                _copy_pressed_face,
                "accent_text",
            ),
            id="copy pressed color",
        ),
        param(
            HistoryThemeCase(
                {"history": {"clear": {"pressed_color": "accent_text"}}},
                _clear_pressed_face,
                "accent_text",
            ),
            id="clear pressed color",
        ),
        param(
            HistoryThemeCase(
                {"history": {"mode": {"pressed_color": "accent_text"}}},
                _mode_pressed_face,
                "accent_text",
            ),
            id="mode pressed color",
        ),
        param(
            HistoryThemeCase({"options": {"color": "accent_text"}}, _option_face, "accent_text"),
            id="options color",
        ),
        param(
            HistoryThemeCase(
                {"history": {"button": {"pressed_color": "accent_text"}}},
                _copy_pressed_face,
                "accent_text",
            ),
            id="copy pressed from the shared table",
        ),
        param(
            HistoryThemeCase(
                {"options": {"pressed_color": "accent_text"}}, _option_pressed_face, "accent_text"
            ),
            id="options pressed color",
        ),
        param(
            HistoryThemeCase(
                {"history": {"mode": {"color": "accent_text"}}}, _mode_face, "accent_text"
            ),
            id="mode color",
        ),
        param(
            HistoryThemeCase(
                {"colors": {"sunset": "#FF8800"}, "options": {"color": "sunset"}},
                _option_face_is_sunset,
                True,
            ),
            id="custom color name",
        ),
        param(
            HistoryThemeCase(
                {"history": {"button": {"edge": {"light_color": "accent_text"}}}},
                _copy_top_edge,
                "accent_text",
            ),
            id="raised edge light side",
        ),
        param(
            HistoryThemeCase(
                {"history": {"button": {"edge": {"shadow_color": "accent_text"}}}},
                _copy_bottom_edge,
                "accent_text",
            ),
            id="raised edge shadow side",
        ),
        param(
            HistoryThemeCase(
                {"history": {"button": {"radius": 11}, "copy": ACCENT}},
                _copy_corner_is_the_face,
                False,
            ),
            id="radius rounds the corner",
        ),
        param(
            HistoryThemeCase({"history": {"clear": {"text": ACCENT}}}, _clear_color, "accent_text"),
            id="clear text color",
        ),
        param(
            HistoryThemeCase(
                {"history": {"mode": {"text": ACCENT}}}, _math_mode_color, "accent_text"
            ),
            id="mode text color",
        ),
        param(
            HistoryThemeCase(
                {"history": {"mode": {"text": {"font": {"min_pt": 15}}}}}, _math_mode_font_size, 15
            ),
            id="mode font size",
        ),
        param(
            HistoryThemeCase(OPTION_FONT, _math_mode_font_size, 9),
            id="options font size leaves the history modes",
        ),
        param(HistoryThemeCase(OPTION_FONT, _option_font_size, 15), id="options font size"),
    ],
)
def test_theme_reaches_the_history(history, qapp, apply_user_theme, case):
    _add(history, "1+2", "3", qapp)
    apply_user_theme(case.table)
    history.update_fonts()
    expected = case.expected
    if isinstance(expected, str):
        expected = get_theme().colors[expected].upper()
    assert case.shown(history) == expected


def test_checked_mode_button_paints_primary_with_its_text(history, qapp, apply_user_theme):
    apply_user_theme({"colors": {"primary": "#123456", "primary_text": "#FFEE00"}})
    button = _mode_button(history, RenderMode.FLAT)
    assert button.isChecked()
    image = button.grab().toImage()
    colors = [image.pixelColor(x, y) for x in range(image.width()) for y in range(image.height())]
    assert "#123456" in {c.name() for c in colors}
    # Antialiased text never reaches the exact color: yellow pixels, not the old text's
    assert any(c.red() > 150 and c.blue() < 64 for c in colors)


def test_raised_edge_shadow_is_darker_than_the_button(history, qapp, apply_user_theme):
    _add(history, "1+2", "3", qapp)
    # background_light is the face of history.copy; the relation means nothing on arbitrary colors
    apply_user_theme({"colors": {"background_light": "#C0C0C0", "button_shadow": "#101010"}})
    button = _item_widget(history, 0)._copy_btn
    shadow, face = QColor(_pixel(button, 11, 21)), QColor(_pixel(button, 2, 11))
    assert shadow.lightness() < face.lightness()


def test_open_items_take_the_theme_sizes(history, qapp, apply_user_theme):
    _add(history, "1+2", "3", qapp)
    history.set_mode(RenderMode.MATH)
    item = _item_widget(history, 0)
    apply_user_theme({"history": {"icon_button_size": 30, "math_font_size": 40}})
    qapp.processEvents()
    margin = item.layout().contentsMargins().bottom()
    assert (item._copy_btn.width(), item._remove_btn.width(), item._font.pointSize()) == (
        30,
        30,
        40,
    )
    assert item._copy_btn.y() == item.height() - margin - 30


def test_icon_button_size_applies_to_new_items(history, qapp, apply_user_theme):
    apply_user_theme({"history": {"icon_button_size": 30}})
    _add(history, "1+2", "3", qapp)
    assert _item_widget(history, 0)._copy_btn.width() == 30


# ===================================================================
# Wrap expression
# ===================================================================


class TestWrapExpression:
    """wrap_expression splits long lines at operator symbols."""

    def test_empty_returns_empty(self, history):
        fm = history.list.fontMetrics()
        assert wrap_expression("", fm, 200) == ""

    def test_short_no_wrap(self, history):
        fm = history.list.fontMetrics()
        assert "\n" not in wrap_expression("1 + 2", fm, 9999)

    def test_narrow_width_wraps(self, history):
        fm = history.list.fontMetrics()
        result = wrap_expression("1 + 2 + 3 + 4 + 5 + 6 + 7 + 8", fm, 40)
        assert "\n" in result

    # (expression, its width budget from the font metrics)
    @pytest.mark.parametrize(
        "expr, budget",
        [
            pytest.param("100 + 200 + 300 + 400 + 500 + 600 + 700", lambda fm: 80, id="sums"),
            pytest.param(
                "100 + 200 + 300",
                lambda fm: fm.horizontalAdvance("100 + 200 +") - 1,
                id="plus overflows",
            ),
            pytest.param(
                "sin(1) + cos(2) + 3",
                lambda fm: fm.horizontalAdvance("sin(1) + cos(2)") - 1,
                id="close paren overflows",
            ),
        ],
    )
    def test_all_lines_within_budget(self, history, expr, budget):
        fm = history.list.fontMetrics()
        max_w = budget(fm)
        for line in wrap_expression(expr, fm, max_w).split("\n"):
            assert fm.horizontalAdvance(line) <= max_w


# ===================================================================
# Highlight / selection
# ===================================================================


class TestHighlight:
    """highlight_item / clear_highlight drive QListWidget selection."""

    @pytest.mark.parametrize(
        "target, expected",
        [
            (1, 1),
            (99, -1),
        ],
        ids=["valid-row", "out-of-range"],
    )
    def test_highlight_item(self, history, qapp, target, expected):
        _add(history, "1+1", "2", qapp)
        _add(history, "2+2", "4", qapp)

        history.highlight_item(target)
        qapp.processEvents()

        assert history.list.currentRow() == expected

    def test_clear_highlight(self, history, qapp):
        _add(history, "1+1", "2", qapp)

        history.highlight_item(0)
        qapp.processEvents()
        history.clear_highlight()
        qapp.processEvents()

        assert history.list.currentRow() == -1


# ===================================================================
# Edge cases
# ===================================================================


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_empty_expression(self, history, qapp):
        _add(history, "", "0", qapp)
        assert history.list.count() == 1

    def test_remove_last_item(self, history, qapp):
        _add(history, "1+1", "2", qapp)

        history._remove_item(history.list.item(0))
        qapp.processEvents()

        assert history.list.count() == 0
        assert len(history._item_widgets) == 0

    def test_double_clear(self, history, qapp):
        _add(history, "1+1", "2", qapp)

        history.clear_history()
        history.clear_history()
        qapp.processEvents()

        assert history.list.count() == 0

    def test_mode_switch_on_empty_history(self, history, qapp):
        history.set_mode(RenderMode.RAW)
        qapp.processEvents()
        history.set_mode(RenderMode.FLAT)
        qapp.processEvents()

        assert history.list.count() == 0

    def test_scroll_to_bottom_on_add(self, history, qapp):
        for i in range(20):
            _add(history, f"{i}+1", str(i + 1), qapp)

        sb = history.list.verticalScrollBar()
        assert sb.value() == sb.maximum()
