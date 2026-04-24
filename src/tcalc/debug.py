from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, Literal, TypeVar

import calc_native
from PySide6.QtWidgets import QLineEdit

if TYPE_CHECKING:
    from tcalc.ui.widgets.calc.display.expression.expression import Expression

from tcalc.ui.widgets.math import (
    ExpressionNode,
    ExpressionSlot,
    FractionWidget,
    ParenWidget,
    PowWidget,
    RootWidget,
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
        elif isinstance(t.data, calc_native.LatexToken):
            val = f"Latex({t.data.kind.name})"
        else:
            val = str(t)
        out.append(f"{kind}: {val}")
    _log.debug("TOKENS -> %s", out)


def _fmt_math_nodes(nodes: list[calc_native.MathNode], indent: int = 0) -> list[str]:
    pad = "  " * indent
    lines: list[str] = []
    for n in nodes:
        kind = n.kind
        if kind == calc_native.MathNodeKind.Text:
            lines.append(f"{pad}Text {n.as_text().text!r}")
        elif kind == calc_native.MathNodeKind.Paren:
            p = n.as_paren()
            close = "" if p.has_close else " (unmatched)"
            lines.append(f"{pad}Paren[{p.kind.name}]{close}")
            lines.extend(_fmt_math_nodes(p.children, indent + 1))
        else:
            lx = n.as_latex()
            lines.append(f"{pad}Latex[{lx.kind.name}]")
            lines.append(f"{pad}  left:")
            lines.extend(_fmt_math_nodes(lx.left, indent + 2))
            lines.append(f"{pad}  right:")
            lines.extend(_fmt_math_nodes(lx.right, indent + 2))
    return lines


def debug_math_nodes(nodes: list[calc_native.MathNode]) -> None:
    """Log a MathNode tree in readable indented form."""
    _log.debug("MATH_NODES ->")
    for line in _fmt_math_nodes(nodes):
        _log.debug(line)


#
#
# LatexNode Debugger
# ===================================================
_W = TypeVar("_W", bound=ExpressionNode)


@dataclass
class SegInfo:
    """One segment inside a SlotInfo."""

    kind: Literal["edit", "node", "glyph"]
    text: str | None = None  # QLineEdit text (kind=="edit")
    name: str | None = None  # QLineEdit objectName, stripped (kind=="edit")
    node: NodeInfo | None = None  # nested node  (kind=="node")
    glyph_cls: str | None = None  # e.g. "CurlyBrace" (kind=="glyph")

    def _fmt(self, index: int, indent: str) -> str:
        if self.kind == "edit":
            display = repr(self.text) if self.text else '""'
            return f"{indent}  [{index}] QLineEdit({self.name}) {display}"
        if self.kind == "node":
            return f"{indent}  [{index}] ->"
        # glyph
        return f"{indent}  [{index}] {self.glyph_cls}"


@dataclass
class SlotInfo:
    """Snapshot of one ExpressionSlot."""

    key: str
    paren: tuple[str | None, str | None] | None
    segments: list[SegInfo] = field(default_factory=list)

    @property
    def edit_count(self) -> int:
        return sum(1 for s in self.segments if s.kind == "edit")

    @property
    def node_count(self) -> int:
        return sum(1 for s in self.segments if s.kind == "node")

    @property
    def glyph_count(self) -> int:
        return sum(1 for s in self.segments if s.kind == "glyph")

    @property
    def nodes(self) -> list[NodeInfo]:
        return [s.node for s in self.segments if s.kind == "node" and s.node]

    def _fmt(self, depth: int) -> list[str]:
        indent = "  " * depth
        paren_info = f"  paren={self.paren}" if self.paren else ""
        lines = [f"{indent}Slot[{self.key}] segments={len(self.segments)}{paren_info}"]
        for i, seg in enumerate(self.segments):
            lines.append(seg._fmt(i, indent))
            if seg.kind == "node" and seg.node:
                lines.extend(seg.node._fmt(depth + 1))
        return lines


@dataclass
class NodeInfo(Generic[_W]):
    """Snapshot of one ExpressionNode."""

    widget: _W
    cls_name: str
    paren_kind: calc_native.ParenKind | None = None
    has_open: bool | None = None  # only for ParenWidget
    has_close: bool | None = None  # only for ParenWidget
    slots: list[SlotInfo] = field(default_factory=list)

    def _fmt(self, depth: int) -> list[str]:
        indent = "  " * depth
        lines = [f"{indent}Node<{self.cls_name}>"]
        for slot in self.slots:
            lines.extend(slot._fmt(depth + 1))
        return lines


@dataclass
class TreeInfo:
    """Full snapshot of an Expression widget's render tree."""

    root: SlotInfo
    plain_text: str

    all_nodes: list[NodeInfo] = field(default_factory=list)
    all_slots: list[SlotInfo] = field(default_factory=list)
    all_edits: list[SegInfo] = field(default_factory=list)

    def _nodes_of_type(self, cls: type[_W]) -> list[NodeInfo[_W]]:
        return [n for n in self.all_nodes if isinstance(n.widget, cls)]

    @property
    def parens(self) -> list[NodeInfo[ParenWidget]]:
        return self._nodes_of_type(ParenWidget)

    @property
    def fracs(self) -> list[NodeInfo[FractionWidget]]:
        return self._nodes_of_type(FractionWidget)

    @property
    def pows(self) -> list[NodeInfo[PowWidget]]:
        return self._nodes_of_type(PowWidget)

    @property
    def roots(self) -> list[NodeInfo[RootWidget]]:
        return self._nodes_of_type(RootWidget)

    def __str__(self) -> str:
        sep = "=" * 42
        header = (
            f"{sep}[Expression Tree] "
            f"slots={len(self.all_slots)}  "
            f"nodes={len(self.all_nodes)}  "
            f"edits={len(self.all_edits)}"
            f"{sep}"
        )
        lines = [header]
        lines.extend(self.root._fmt(0))
        lines.append(f"[plain_text] {self.plain_text!r}")
        return "\n".join(lines)


def snapshot_tree(widget: "Expression") -> TreeInfo:
    """Walk the expression tree and return a structured TreeInfo snapshot."""
    info = TreeInfo(root=SlotInfo(key="", paren=None), plain_text=widget.get_plain_text())

    def _walk_slot(slot: ExpressionSlot) -> SlotInfo:
        si = SlotInfo(key=slot._key, paren=slot._paren)
        info.all_slots.append(si)
        for seg in slot._segments:
            if isinstance(seg, QLineEdit):
                name = seg.objectName().removeprefix("displayExpression_")
                ei = SegInfo(kind="edit", text=seg.text(), name=name)
                si.segments.append(ei)
                info.all_edits.append(ei)
            elif isinstance(seg, ExpressionNode):
                ni = _walk_node(seg)
                si.segments.append(SegInfo(kind="node", node=ni))
            else:
                si.segments.append(SegInfo(kind="glyph", glyph_cls=type(seg).__name__))
        return si

    def _walk_node(node: ExpressionNode) -> NodeInfo:
        ni: NodeInfo = NodeInfo(
            widget=node,
            cls_name=type(node).__name__,
        )
        info.all_nodes.append(ni)
        if isinstance(node, ParenWidget):
            ni.paren_kind = node.PAREN_KIND
            ni.has_open = node._open_token is not None
            ni.has_close = node._close_token is not None
        for slot in (node._left_slot, node._right_slot):
            if slot is not None:
                ni.slots.append(_walk_slot(slot))
        return ni

    info.root = _walk_slot(widget._root)
    return info


#
# Expression Debug logger
def dump_expression_tree(root: ExpressionSlot, plain_text: str) -> None:
    """Snapshot the tree from a root slot and log it."""

    editor = root._editor
    if editor is None:
        raise RuntimeError("ExpressionSlot editor is not set")
    info = snapshot_tree(editor)

    for line in str(info).splitlines():
        _log.info(line)
