from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .styles import apply_styles
from .window import MainWindow


def run_app(argv: Optional[Sequence[str]] = None) -> int:
    app = QApplication(list(argv) if argv is not None else [])
    app.setApplicationName("TCalc")
    app.setWindowIcon(QIcon.fromTheme("accessories-calculator"))
    apply_styles(app)

    window = MainWindow()
    window.show()

    return int(app.exec())
