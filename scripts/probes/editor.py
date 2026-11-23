#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""probe editor: a text in the app's editor, then key steps, the widget tree and cursor after each."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from probes.app import app_window, save_png, settle
from probes.options import Options, read_inputs
from probes.rows import Layer, ProbeError, Row, format_rows
from probes.tree import tree_row
from tcalc.core.ops import Operation
from tcalc.ui.window import MainWindow

# a step that is one key, pressed as the user presses it, through the app's keyboard handler
KEY_STEPS: dict[str, Qt.Key] = {
    "left": Qt.Key.Key_Left,
    "right": Qt.Key.Key_Right,
    "up": Qt.Key.Key_Up,
    "down": Qt.Key.Key_Down,
    "bs": Qt.Key.Key_Backspace,
}
STEP_SEPARATOR = ":"


def _focused() -> QWidget:
    focus = QApplication.focusWidget()
    # the window is shown and active, so one of its fields holds the focus
    assert focus is not None
    return focus


def _keypad_key(window: MainWindow, name: str) -> None:
    """A keypad button: the controller's own handler for the operation."""
    if name not in Operation.__members__:
        raise ProbeError(f"no operation {name!r}; the names are Operation's, e.g. DIV, POW, ROOT")
    op = Operation[name]
    window.controller.handle_key(op.symbol, op)


def _typed(_window: MainWindow, text: str) -> None:
    QTest.keyClicks(_focused(), text)


# a step that names its argument after the separator: key:DIV, text:12
NAMED_STEPS: dict[str, Callable[[MainWindow, str], None]] = {"key": _keypad_key, "text": _typed}


def _step(window: MainWindow, step: str) -> None:
    key = KEY_STEPS.get(step)
    if key is not None:
        QTest.keyClick(_focused(), key)
        return
    name, separator, argument = step.partition(STEP_SEPARATOR)
    act = NAMED_STEPS.get(name) if separator else None
    if act is None:
        steps = [*KEY_STEPS, *(f"{named}{STEP_SEPARATOR}..." for named in NAMED_STEPS)]
        raise ProbeError(f"no step {step!r}; the steps are {', '.join(steps)}")
    act(window, argument)


def editor_rows(window: MainWindow, text: str, steps: Sequence[str]) -> list[Row]:
    """The tree after the text is set, then after each step; the input column names the step."""
    editor = window.calc_widget.display.editor
    editor.set_plain_text(text)
    settle()
    rows = [tree_row(text, Layer.EDITOR, editor._root)]
    for step in steps:
        _step(window, step)
        settle()
        rows.append(tree_row(step, Layer.EDITOR, editor._root))
    return rows


def run(options: Options) -> int:
    texts = [one.text for one in read_inputs(options)]
    if not texts:
        raise ProbeError("editor needs a TEXT, then the steps")
    text, *steps = texts
    with app_window() as window:
        rows = editor_rows(window, text, steps)
        if options.png is not None:
            # the display, so the editor is drawn on its background
            save_png(window.calc_widget.display, options.png)
    print(format_rows(rows), end="")
    return 0
