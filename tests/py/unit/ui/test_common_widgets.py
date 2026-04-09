#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QWidget

from tcalc.ui.widgets.common.button import OptionGroup
from tcalc.ui.widgets.common.toaster import Toaster, ToastLevel
from tcalc.ui.widgets.common.utils import Align, reposition


class TestOptionGroup:
    """OptionGroup radio-button behaviour."""

    @pytest.fixture
    def group(self, qapp):
        g = OptionGroup(
            [("a", "Alpha"), ("b", "Beta"), ("c", "Gamma")],
            current="b",
        )
        g.show()
        qapp.processEvents()
        yield g
        g.close()
        g.deleteLater()
        qapp.processEvents()

    def test_initial_selection(self, group):
        assert group.current() == "b"

    def test_button_count(self, group):
        assert len(group.buttons()) == 3

    def test_checked_button(self, group):
        assert group.buttons()["b"].isChecked()
        assert not group.buttons()["a"].isChecked()

    def test_set_current_programmatic(self, group, qapp):
        group.set_current("c")
        qapp.processEvents()

        assert group.buttons()["c"].isChecked()
        assert group.current() == "c"

    def test_set_current_does_not_emit(self, group, qapp):
        received = []
        group.selection_changed.connect(lambda key: received.append(key))

        group.set_current("a")
        qapp.processEvents()

        assert len(received) == 0

    def test_click_emits_signal(self, group, qapp):
        received = []
        group.selection_changed.connect(lambda key: received.append(key))

        group.buttons()["a"].setChecked(True)
        qapp.processEvents()

        assert "a" in received

    def test_click_updates_current(self, group, qapp):
        group.buttons()["c"].setChecked(True)
        qapp.processEvents()

        assert group.current() == "c"

    def test_set_current_invalid_key(self, group, qapp):
        """Unknown key must be a no-op, not crash."""
        group.set_current("nonexistent")
        qapp.processEvents()

        assert group.current() == "b"

    def test_size_policy_fixed(self, group):
        sp = group.sizePolicy()
        assert sp.horizontalPolicy() == QSizePolicy.Policy.Fixed
        assert sp.verticalPolicy() == QSizePolicy.Policy.Fixed


class TestToaster:
    """Toaster show / hide lifecycle."""

    @pytest.fixture
    def parent(self, qapp):
        w = QWidget()
        w.resize(300, 200)
        w.show()
        qapp.processEvents()
        yield w
        w.close()
        w.deleteLater()
        qapp.processEvents()

    @pytest.fixture
    def toaster(self, parent):
        return Toaster(parent, duration_ms=50000, fade_ms=10)

    def test_hidden_by_default(self, toaster):
        assert not toaster.isVisible()

    def test_show_toast_makes_visible(self, toaster, qapp):
        toaster.show_toast("Hello")
        qapp.processEvents()

        assert toaster.isVisible()
        assert toaster.text() == "Hello"

    def test_show_toast_sets_text(self, toaster, qapp):
        toaster.show_toast("World", ToastLevel.WARN)
        qapp.processEvents()

        assert toaster.text() == "World"

    def test_toast_replaces_previous(self, toaster, qapp):
        toaster.show_toast("First")
        qapp.processEvents()
        toaster.show_toast("Second")
        qapp.processEvents()

        assert toaster.text() == "Second"
        assert toaster.isVisible()

    def test_alignment_center(self, toaster):
        assert toaster.alignment() == Qt.AlignmentFlag.AlignCenter

    def test_word_wrap_off(self, toaster):
        assert not toaster.wordWrap()


class TestReposition:
    """reposition places child relative to parent."""

    @pytest.fixture
    def parent_child(self, qapp):
        parent = QWidget()
        parent.resize(400, 300)
        parent.show()
        child = QWidget(parent)
        child.resize(40, 20)
        child.show()
        qapp.processEvents()
        yield parent, child
        parent.close()
        parent.deleteLater()
        qapp.processEvents()

    def test_center(self, parent_child):
        _, child = parent_child
        reposition(child, Align.CENTER, Align.CENTER, margin=0)

        assert child.x() == (400 - 40) // 2
        assert child.y() == (300 - 20) // 2

    def test_top_left(self, parent_child):
        _, child = parent_child
        reposition(child, Align.LEFT, Align.TOP, margin=5)

        assert child.x() == 5
        assert child.y() == 5

    def test_bottom_right(self, parent_child):
        _, child = parent_child
        reposition(child, Align.RIGHT, Align.BOTTOM, margin=10)

        assert child.x() == 400 - 40 - 10
        assert child.y() == 300 - 20 - 10

    @pytest.mark.usefixtures("qapp")
    def test_no_parent_noop(self):
        orphan = QWidget()
        orphan.resize(20, 20)
        reposition(orphan, Align.CENTER, Align.CENTER)
        orphan.deleteLater()
