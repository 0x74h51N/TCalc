from __future__ import annotations

import sys

import pytest
from PySide6.QtWidgets import QApplication
import os


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the entire test session."""
    # Silence noisy Qt QPA plugin warnings during tests
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.plugin=false")
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
