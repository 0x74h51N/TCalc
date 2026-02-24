from __future__ import annotations

import logging
from typing import Optional, Sequence

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .styles import apply_styles
from .window import MainWindow


def run_app(argv: Optional[Sequence[str]] = None, *, debug: bool = False) -> int:
    if debug:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s | %(message)s")
    app = QApplication(list(argv) if argv is not None else [])
    app.setApplicationName("TCalc")
    app.setWindowIcon(QIcon.fromTheme("accessories-calculator"))
    apply_styles(app)

    window = MainWindow()

    if debug:
        _attach_debug_hooks(window)

    window.show()

    return int(app.exec())


def _attach_debug_hooks(window: MainWindow) -> None:
    from tcalc.debug import dump_expression_tree

    editor = window.calc_widget.display.editor
    editor.plain_text_changed.connect(
        lambda _: dump_expression_tree(editor._root, editor.get_plain_text())
    )
