#
#
#   TCalc is a native-powered scientific desktop calculator designed
#   for high-performance, precision, and a superior user experience.
#   Copyright (C) <2025>  <Tahsin Önemli>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

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
