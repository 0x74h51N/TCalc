#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""The Qt application a probe needs for the editor's widgets, offscreen and quiet."""

from __future__ import annotations

import os

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

APP_NAME = "TCalc"


def offscreen_app() -> QCoreApplication:
    # a probe opens no window; a variable the caller already set wins
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_LOGGING_RULES", "*=false")
    return QApplication.instance() or QApplication([APP_NAME])
