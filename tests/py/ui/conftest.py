#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "*.warning=false")

if TYPE_CHECKING:
    from tcalc.ui.widgets.calc.display.expression.expression import Expression


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def _user_themes(tmp_path, monkeypatch):
    """The user's own themes folder, empty, so tests never read the real one."""
    folder = tmp_path / "user-themes"
    monkeypatch.setattr("tcalc.theme.user_themes_dir", lambda: folder)
    return folder


# TODO(test themes): test_picture_layer, test_icons, test_color_scheme and test_theme_colors in
# tests/py/unit/ui still use the bundled kitty, retro and sponge themes; move them to test themes
@pytest.fixture
def extreme_theme(_user_themes) -> str:
    """The test-only Extreme theme, installed as a user theme; returns its id."""
    shutil.copytree(Path(__file__).parent / "themes" / "extreme", _user_themes / "extreme")
    return "extreme"


@pytest.fixture
def expression_widget(qapp) -> "Expression":
    """Create a fresh Expression widget for testing."""
    from tcalc.ui.widgets.calc.display.expression.expression import Expression

    widget = Expression()
    widget.show()
    yield widget
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


@pytest.fixture
def set_expression(expression_widget, qapp) -> Callable[[str], None]:
    """Helper to set expression text and process events."""

    def _set(text: str) -> None:
        expression_widget.set_plain_text(text)
        qapp.processEvents()

    return _set
