#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""A slot's widget tree on one line, with | at the cursor."""

from __future__ import annotations

from probes.rows import PLAIN_COLUMN, TEXT_TYPE, Layer, Row
from tcalc.debug import NodeInfo, SegInfo, SlotInfo, snapshot_slot
from tcalc.ui.widgets.math import ExpressionNode, ExpressionSlot

NODE_SUFFIX = "Widget"


def _node(node: NodeInfo[ExpressionNode]) -> str:
    slots = " ; ".join(_slot(slot) for slot in node.slots)
    return f"{node.cls_name.removesuffix(NODE_SUFFIX)}<{slots}>"


def _segment(seg: SegInfo) -> str:
    match seg.kind:
        case "edit":
            return repr(seg.shown_text())
        case "node":
            # a node segment always carries its node; SegInfo types it as optional
            assert seg.node is not None
            return _node(seg.node)
        case "glyph":
            return f"{seg.glyph_cls}"


def _slot(slot: SlotInfo) -> str:
    return " ".join(_segment(seg) for seg in slot.segments)


def tree_row(text: str, layer: Layer, root: ExpressionSlot) -> Row:
    """The slot's tree as the row's value, and the text it serializes to beside it."""
    info = snapshot_slot(root)
    return Row(text, layer, TEXT_TYPE, _slot(info.root), ((PLAIN_COLUMN, info.plain_text),))
