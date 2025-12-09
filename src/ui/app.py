from __future__ import annotations

from typing import Iterable, Optional, Sequence

from PySide6.QtWidgets import QApplication

from .window import MainWindow
from .styles import apply_styles


def run_app(argv: Optional[Sequence[str]] = None) -> int:
    app = QApplication(list(argv) if argv is not None else [])
    apply_styles(app)

    window = MainWindow()
    window.show()

    return int(app.exec())
