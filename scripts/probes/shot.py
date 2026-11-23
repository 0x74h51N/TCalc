#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""probe shot: the app's whole window with a text typed in, at a size and a theme, as a PNG."""

from __future__ import annotations

from PySide6.QtCore import QSize

from probes.app import app_window, save_png, settle
from probes.options import Options, read_inputs
from probes.rows import Layer, ProbeError, Row, format_rows, text_row
from tcalc.ui.window import MainWindow

SIZE_SEPARATOR = "x"


def _size(text: str) -> QSize:
    width, separator, height = text.partition(SIZE_SEPARATOR)
    if not (separator and width.isdigit() and height.isdigit()):
        raise ProbeError(f"--size {text!r} is not WIDTHxHEIGHT, e.g. 800x600")
    return QSize(int(width), int(height))


def window_rows(window: MainWindow, text: str) -> list[Row]:
    """The text in the editor, and what the editor and the result line then show."""
    display = window.calc_widget.display
    display.editor.set_plain_text(text)
    settle()
    return [
        text_row(text, Layer.EDITOR, display.editor.get_plain_text()),
        text_row(text, Layer.DISPLAY, display.result.result_label.text()),
    ]


def run(options: Options) -> int:
    if options.png is None:
        raise ProbeError("shot needs --png FILE")
    size = _size(options.size) if options.size is not None else None
    texts = [one.text for one in read_inputs(options)]
    rows: list[Row] = []
    # a window per text, so no result line carries over from the text before
    for index, text in enumerate(texts):
        with app_window(options.theme) as window:
            if size is not None:
                window.resize(size)
            rows += window_rows(window, text)
            if index == len(texts) - 1:
                save_png(window, options.png)
    print(format_rows(rows), end="")
    return 0
