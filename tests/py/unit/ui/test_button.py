#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtCore import QEvent

from tcalc.ui.widgets.common.button import OptionGroup


def _options_look(look):
    return look.options


class TestOptionGroup:
    """OptionGroup radio-button behaviour."""

    @pytest.fixture
    def group(self, qapp, monkeypatch):
        options = SimpleNamespace(edge=SimpleNamespace(width=0), radius=4)
        monkeypatch.setattr(
            "tcalc.ui.widgets.common.button.get_theme",
            lambda: SimpleNamespace(look=SimpleNamespace(options=options)),
        )
        g = OptionGroup([("a", "Alpha"), ("b", "Beta"), ("c", "Gamma")], "b", _options_look)
        g.show()
        qapp.processEvents()
        yield g
        g.close()
        g.deleteLater()
        # A live fit timer would fire after the patch is gone, on the real theme
        qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_initial_selection(self, group):
        assert group.current() == "b"

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

        assert received == ["a"]

    def test_click_updates_current(self, group, qapp):
        group.buttons()["c"].setChecked(True)
        qapp.processEvents()

        assert group.current() == "c"

    def test_set_current_invalid_key(self, group, qapp):
        """Unknown key must be a no-op, not crash."""
        group.set_current("nonexistent")
        qapp.processEvents()

        assert group.current() == "b"
