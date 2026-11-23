#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""probe render: a text rendered read-only, as the result line renders it, with the renderer's log."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from probes.app import save_png, settle, styled_app
from probes.options import Options, read_inputs
from probes.rows import Layer, Row, format_rows
from probes.tree import tree_row
from tcalc.core.parser import tokenize
from tcalc.ui.widgets.math import ExpressionSlot
from tcalc.ui.widgets.math.renderer.expression_node import InputKind
from tcalc.ui.widgets.math.renderer.math_render import MathRender
from tcalc.ui.widgets.utils import InputAlign

# MathRender logs here, at debug, what it skipped (render_node swallows its exceptions)
RENDER_LOGGER = "tcalc.ui"
SLOT_KEY = "probe"


class _Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@contextmanager
def _logged() -> Iterator[_Records]:
    logger = logging.getLogger(RENDER_LOGGER)
    handler = _Records()
    level = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(level)


def _log_row(text: str, record: logging.LogRecord) -> Row:
    error = record.exc_info[1] if record.exc_info is not None else None
    cause = f": {type(error).__name__}: {error}" if error is not None else ""
    return Row(text, Layer.LOG, record.levelname, record.getMessage() + cause)


def render_slot(text: str) -> tuple[ExpressionSlot, list[Row]]:
    """A fresh slot, built as the result line builds its own, with the text rendered into it."""
    slot = ExpressionSlot(kind=InputKind.MAIN, key=SLOT_KEY, align=InputAlign.RIGHT)
    with _logged() as log:
        MathRender(read_only=True).render_node(slot.default_input(), tokenize(text))
        slot.show()
        settle()
    return slot, [
        *(_log_row(text, record) for record in log.records),
        tree_row(text, Layer.TREE, slot),
    ]


def run(options: Options) -> int:
    with styled_app():
        rendered = [render_slot(one.text) for one in read_inputs(options)]
        if options.png is not None and rendered:
            save_png(rendered[-1][0], options.png)
    print(format_rows([row for _, rows in rendered for row in rows]), end="")
    return 0
