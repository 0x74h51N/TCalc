#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QWidget

from tcalc.ui.widgets.common.toaster import Toaster


class TestToaster:
    """Toaster show / hide lifecycle."""

    @pytest.fixture
    def parent(self, qapp, monkeypatch):
        toast = SimpleNamespace(radius=4)
        monkeypatch.setattr(
            "tcalc.ui.widgets.common.toaster.get_theme",
            lambda: SimpleNamespace(look=SimpleNamespace(toast=toast)),
        )
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
        assert toaster.isHidden()

    def test_show_toast_makes_visible(self, toaster, qapp):
        toaster.show_toast("Hello")
        qapp.processEvents()

        assert not toaster.isHidden()
        assert toaster.text() == "Hello"

    def test_show_toast_sets_the_level(self, toaster, qapp):
        toaster.show_toast("World", "warn")
        qapp.processEvents()

        assert toaster.property("toastLevel") == "warn"

    def test_fade_done_hides_the_toast(self, toaster):
        toaster.show_toast("Hello")
        toaster._on_fade_done()
        assert toaster.isHidden()

    def test_toast_replaces_previous(self, toaster, qapp):
        toaster.show_toast("First")
        qapp.processEvents()
        toaster.show_toast("Second")
        qapp.processEvents()

        assert toaster.text() == "Second"
        assert not toaster.isHidden()
