#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""The Qt application a probe or a UI test needs, offscreen, quiet and isolated from the user's files."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

import tcalc.app_state
from probes.rows import ProbeError
from tcalc.theme import ThemeError
from tcalc.ui.app import apply_saved_theme
from tcalc.ui.styles import apply_theme
from tcalc.ui.window import MainWindow

APP_NAME = "TCalc"
# the editor lays out through chains of 0 ms timers that the app's event loop runs as they
# come; measured 2026-11-23: one processEvents pass leaves a grab blank, 50 ms draws it
SETTLE_MS = 50


def offscreen_app() -> QApplication:
    # a probe opens no window; a variable the caller already set wins
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_LOGGING_RULES", "*=false")
    app = QApplication.instance() or QApplication([APP_NAME])
    # instance() is typed as the core application; only a QApplication is ever made here
    assert isinstance(app, QApplication)
    return app


def isolate_app(folder: Path) -> None:
    """Settings, history and the app state under folder, so no window touches the user's own."""
    QSettings.setPath(
        QSettings.Format.NativeFormat, QSettings.Scope.UserScope, str(folder / "config")
    )
    # QStandardPaths reads it on every call, so the history file moves with it
    os.environ["XDG_DATA_HOME"] = str(folder / "data")
    tcalc.app_state._app_state = None


@contextmanager
def styled_app(theme: str | None = None) -> Iterator[QApplication]:
    """The app styled as it starts, or in the named theme, on settings and history of a temp folder."""
    app = offscreen_app()
    with tempfile.TemporaryDirectory() as folder:
        isolate_app(Path(folder))
        apply_saved_theme(app)
        if theme is not None:
            try:
                apply_theme(app, theme)
            except ThemeError as error:
                raise ProbeError(f"no theme {theme!r}: {error}") from error
        yield app


@contextmanager
def app_window(theme: str | None = None) -> Iterator[MainWindow]:
    """The app's window as the app starts it."""
    with styled_app(theme):
        window = MainWindow()
        window.show()
        window.activateWindow()
        settle()
        try:
            yield window
        finally:
            window.close()
            settle()


def save_png(widget: QWidget, path: Path) -> None:
    # QPixmap.save reports a failed write by returning False
    if not widget.grab().save(str(path)):
        raise ProbeError(f"could not write {path}")


def settle() -> None:
    """Run the event loop for a moment, as the app's own loop runs between two keys."""
    QTest.qWait(SETTLE_MS)
