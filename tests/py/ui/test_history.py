#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import calc_native
import pytest
from PySide6.QtCore import QPoint, Qt

from tcalc.app_state import RenderMode, get_app_state
from tcalc.core.parser import tokenize
from tcalc.theme import load_theme
from tcalc.ui.config import history_style as style
from tcalc.ui.styles import apply_theme
from tcalc.ui.widgets.history.history import History, HistoryItem
from tcalc.ui.widgets.history.storage import HistoryEntry
from tcalc.ui.widgets.history.utils import wrap_expression


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
        assert w.minimumHeight() >= int(style["item_min_height"])

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
        assert item.sizeHint().height() >= int(style["item_min_height"])

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
