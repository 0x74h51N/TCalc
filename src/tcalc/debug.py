from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import calc_native
from PySide6.QtWidgets import QLineEdit, QWidget

if TYPE_CHECKING:
    from tcalc.ui.widgets.calc.display.expression.expression_node import (
        ExpressionSlot,
    )

_log = logging.getLogger("tcalc.debug")


def debug_tokens(tokens: list[calc_native.Token]) -> None:
    """Log token list in readable format."""
    out = []
    for t in tokens:
        kind = t.kind.name
        if isinstance(t.data, calc_native.ParenToken):
            val = t.data.symbol
        elif isinstance(t.data, calc_native.NumberToken):
            val = t.data.value
        elif isinstance(t.data, calc_native.OpToken):
            val = t.symbol
        elif isinstance(t.data, calc_native.ExprToken):
            val = f"Expr({t.data.kind.name})"
        else:
            val = str(t)
        out.append(f"{kind}: {val}")
    _log.debug("TOKENS -> %s", out)


def dump_expression_tree(root: ExpressionSlot, get_plain_text: str) -> None:
    """Walk and log the full expression widget tree."""
    from tcalc.ui.widgets.calc.display.expression.expression_node import (
        ExpressionNode,
        ExpressionSlot,
    )

    counts: dict[str, int] = {"slots": 0, "nodes": 0, "edits": 0}
    lines: list[str] = []

    def _walk(widget: QWidget, depth: int = 0) -> None:
        indent = "  " * depth
        if isinstance(widget, ExpressionSlot):
            counts["slots"] += 1
            paren_info = f"  paren={widget._paren}" if widget._paren else ""
            lines.append(
                f"{indent}Slot[{widget._key}] segments={len(widget._segments)}{paren_info}"
            )
            for i, seg in enumerate(widget._segments):
                if isinstance(seg, QLineEdit):
                    counts["edits"] += 1
                    name = seg.objectName().removeprefix("displayExpression_")
                    text = seg.text()
                    display = repr(text) if text else '""'
                    lines.append(f"{indent}  [{i}] QLineEdit({name}) {display}")
                elif isinstance(seg, ExpressionNode):
                    lines.append(f"{indent}  [{i}] ->")
                    _walk(seg, depth + 1)
                else:
                    lines.append(f"{indent}  [{i}] {type(seg).__name__}")

        elif isinstance(widget, ExpressionNode):
            counts["nodes"] += 1
            cls_name = type(widget).__name__
            lines.append(f"{indent}Node<{cls_name}>")
            if widget._left_slot:
                _walk(widget._left_slot, depth + 1)
            if widget._right_slot:
                _walk(widget._right_slot, depth + 1)

        else:
            lines.append(f"{indent}{type(widget).__name__}")

    _walk(root)

    sep = "=" * 42
    header = f"{sep}[Expression Tree] slots={counts['slots']}  nodes={counts['nodes']}  edits={counts['edits']}{sep}"
    _log.info(header)
    for line in lines:
        _log.info(line)
    _log.info("[plain_text] %r", get_plain_text)
