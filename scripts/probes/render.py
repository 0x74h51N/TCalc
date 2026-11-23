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
from probes.rows import Layer, Row, format_rows, type_name
from probes.tree import tree_row
from tcalc.core.parser import tokenize
from tcalc.ui.widgets.math import ExpressionSlot
from tcalc.ui.widgets.math.renderer.expression_node import InputKind
from tcalc.ui.widgets.math.renderer.math_render import MathRender
from tcalc.ui.widgets.utils import InputAlign

# render_node swallows its exceptions and logs them here, at debug, with the exception
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
    # only a record that carries an exception is shown, so exc_info is set
    assert record.exc_info is not None
    error = record.exc_info[1]
    return Row(text, Layer.LOG, type_name(error), f"{record.getMessage()}: {error}")


def render_slot(text: str) -> tuple[ExpressionSlot, list[Row]]:
    """A fresh read-only slot, built as the result line builds its own, with the text rendered into it."""
    slot = ExpressionSlot(kind=InputKind.MAIN, key=SLOT_KEY, align=InputAlign.RIGHT)
    with _logged() as log:
        MathRender(read_only=True).render_node(slot.default_input(), tokenize(text))
        slot.show()
        settle()
    # the other records repeat the node lists `probe layers` already prints
    failures = [_log_row(text, record) for record in log.records if record.exc_info is not None]
    return slot, [*failures, tree_row(text, Layer.TREE, slot)]


def run(options: Options) -> int:
    with styled_app(options.theme):
        rendered = [render_slot(one.text) for one in read_inputs(options, grouped=False)]
        if options.png is not None and rendered:
            save_png(rendered[-1][0], options.png)
    print(format_rows([row for _, rows in rendered for row in rows]), end="")
    return 0
