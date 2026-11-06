#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import pytest
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from tcalc.ui.widgets.calc.display.expression.expression import Expression


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def _user_themes(tmp_path, monkeypatch):
    """The user's own themes folder, empty, so tests never read the real one."""
    folder = tmp_path / "user-themes"
    monkeypatch.setattr("tcalc.theme.user_themes_dir", lambda: folder)
    return folder


@pytest.fixture(autouse=True)
def _test_themes(_user_themes, monkeypatch):
    """No test here reads a bundled theme or the user's folder: dark and light are the test
    files, and extreme is the one custom theme."""
    monkeypatch.setattr("tcalc.theme.BUILT_IN_DIR", Path(__file__).parent / "themes")


@pytest.fixture
def theme_table(monkeypatch):
    """Makes the variant "user" answer with a table, and returns its name."""
    from tcalc.theme import _read

    def install(table: dict[str, object], base: str = "dark") -> str:
        def read(variant: str) -> dict[str, object]:
            if variant == "user":
                return {"name": "User", "base": base, **table}
            return _read(variant)

        monkeypatch.setattr("tcalc.theme._read", read)
        return "user"

    return install


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
