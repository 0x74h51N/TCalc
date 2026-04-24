#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import calc_native
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLineEdit,
    QWidget,
)
from shiboken6 import isValid

from tcalc.ui.widgets.utils import apply_scaled_fonts

from ..utils import update_autowidth
from .expression_node import ExpressionNode, ExpressionSlot, InputKind
from .widgets import (
    BraceWidget,
    BracketWidget,
    FractionWidget,
    ParenWidget,
    PowWidget,
    RootWidget,
    RoundParenWidget,
)

if TYPE_CHECKING:
    from tcalc.ui.widgets.calc.display.expression.expression import Expression


_log = logging.getLogger("tcalc.ui.math")


class MathRender(QWidget):
    rendering = Signal(bool)
    LATEX_KIND_MAP: dict[calc_native.LatexKind, type[ExpressionNode]] = {
        FractionWidget.LATEX_KIND: FractionWidget,
        PowWidget.LATEX_KIND: PowWidget,
        RootWidget.LATEX_KIND: RootWidget,
    }

    PAREN_KIND_MAP: dict[calc_native.ParenKind, type[ParenWidget]] = {
        BraceWidget.PAREN_KIND: BraceWidget,
        RoundParenWidget.PAREN_KIND: RoundParenWidget,
        BracketWidget.PAREN_KIND: BracketWidget,
    }

    def __init__(self, read_only: bool = False) -> None:
        super().__init__()
        self._rendering: bool = False
        self._read_only: bool = read_only
        self._editor: Expression
        self._pending_parens: dict[calc_native.ParenKind, list[ParenWidget]] = {}

    @property
    def is_rendering(self) -> bool:
        return self._rendering

    @is_rendering.setter
    def is_rendering(self, value: bool) -> None:
        if self._rendering == value:
            return
        self._rendering = value
        self.rendering.emit(value)

    @property
    def pending_parens(self) -> dict[calc_native.ParenKind, list[ParenWidget]]:
        return self._pending_parens

    @pending_parens.setter
    def pending_parens(
        self, pending_parens: dict[calc_native.ParenKind, list[ParenWidget]]
    ) -> None:
        self._pending_parens = pending_parens

    @property
    def editor(self) -> Expression:
        return self._editor

    @editor.setter
    def editor(self, editor: Expression) -> None:
        self._editor = editor

    def insert_node(
        self,
        slot: ExpressionSlot,
        seg: QLineEdit,
        prefix_tokens: list[calc_native.Token],
        node: ExpressionNode,
        suffix: bool = True,
    ) -> QLineEdit | None:
        """Insert a node widget into slot: [prefix | node | suffix]."""

        idx = slot.index_of(seg)

        seg.setText(calc_native.tokens_to_text(prefix_tokens, self.seg_after_node(seg)))
        seg.setObjectName("prefix")
        slot.insert_widget(idx + 1, node)
        if suffix:
            suffix_le = slot.insert_input(idx + 2)
            suffix_le.setObjectName("suffix")
            return suffix_le
        return None

    def seg_after_node(self, seg: QLineEdit) -> bool:
        """Check if the segment immediately follows an ExpressionNode in its slot."""
        slot = seg.parent()
        if not isinstance(slot, ExpressionSlot):
            return False
        idx = slot.index_of(seg)
        return idx > 0 and isinstance(slot._segments[idx - 1], ExpressionNode)

    def normalize_text(self, seg: QLineEdit, tokens: list[calc_native.Token]) -> None:
        """Normalize text aliases to symbols (add -> + or floor -> ⌊)."""
        text = seg.text()
        new_text = calc_native.tokens_to_text(tokens, self.seg_after_node(seg))
        if new_text != text:
            cursor_pos = seg.cursorPosition()

            # Find new cursor by normali"zing text before cursor
            # Tokens before/at cursor determine new position
            prefix_tokens = [t for t in tokens if t.start_pos < cursor_pos]

            new_cursor = len(calc_native.tokens_to_text(prefix_tokens))
            seg.setText(new_text)
            seg.setCursorPosition(min(new_cursor, len(new_text)))

    def _build_paren(self, node: calc_native.ParenNode) -> ExpressionNode:
        paren_cls = self.PAREN_KIND_MAP[node.kind]

        open_tok = calc_native.ParenToken(calc_native.ParenType.Open, node.kind)
        close_tok = (
            calc_native.ParenToken(calc_native.ParenType.Close, node.kind)
            if node.has_close
            else None
        )
        widget = paren_cls(open_tok, close_tok)
        if not node.has_close:
            self._pending_parens.setdefault(node.kind, []).append(widget)
        return widget

    def _build_latex(self, node: calc_native.LatexNode) -> ExpressionNode:
        widget_cls = self.LATEX_KIND_MAP[node.kind]
        return widget_cls()

    def _render_row(
        self,
        seg: QLineEdit,
        nodes: list[calc_native.MathNode],
        dirty_inputs: set[QLineEdit],
        focus_queue: list[ExpressionNode],
    ) -> None:
        if not isValid(seg):
            return
        slot = seg.parent()
        if not isinstance(slot, ExpressionSlot):
            return

        cur_seg: QLineEdit = seg
        cur_seg.setText("")
        dirty_inputs.add(cur_seg)

        for node in nodes:
            kind = node.kind
            if kind == calc_native.MathNodeKind.Text:
                cur_seg.setText(node.as_text().text)
                cur_seg.setObjectName("prefix")

                dirty_inputs.add(cur_seg)
                continue

            widget: ExpressionNode
            rows: list[list[calc_native.MathNode]]
            if kind == calc_native.MathNodeKind.Paren:
                paren = node.as_paren()
                widget = self._build_paren(paren)
                tail_needed = paren.has_close
                rows = [paren.children]
            else:
                latex = node.as_latex()
                widget = self._build_latex(latex)
                tail_needed = True
                rows = [latex.left, latex.right]

            if not self._read_only:
                widget.editor = self.editor

            idx = slot.index_of(cur_seg)
            if idx < 0:
                return

            slot.insert_widget(idx + 1, widget)

            suffix_seg: QLineEdit | None = None
            if tail_needed:
                suffix_seg = slot.insert_input(idx + 2)
                suffix_seg.setObjectName("suffix")
                dirty_inputs.add(suffix_seg)

            dirty_inputs.update(widget.line_edits())
            focus_queue.append(widget)

            slots = (widget._left_slot, widget._right_slot)
            for child_slot, child_nodes in zip(slots, rows):
                if child_slot is not None and child_nodes:
                    self._render_row(
                        child_slot.default_input(), child_nodes, dirty_inputs, focus_queue
                    )

            if suffix_seg is None:
                return
            cur_seg = suffix_seg

    def render_node(self, seg, tokenized: calc_native.TokensBranch) -> None:
        from tcalc.debug import debug_math_nodes

        dirty_inputs: set[QLineEdit] = set()
        focus_queue: list[ExpressionNode] = []
        try:
            nodes = calc_native.build_math_nodes(tokenized, self.seg_after_node(seg))
            debug_math_nodes(nodes)
            self._render_row(seg, nodes, dirty_inputs, focus_queue)
            if not self._read_only:
                for widget in focus_queue:
                    widget.focus_default()
        except Exception:
            _log.debug("_add_exp_node failed", exc_info=True)
        finally:
            for le in dirty_inputs:
                if self._read_only:
                    le.setReadOnly(True)
                    le.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                update_autowidth(le)

    @staticmethod
    def update_line_fonts(
        lines: list[QLineEdit],
        sample: QWidget,
        base_font: int,
        max_pt: int,
        config: dict | None = None,
    ):
        for le in lines:
            kind_str = le.property("LatexKind")
            scale = float(config.get(f"scale_{kind_str}", 1.0)) if config else 1.0
            # Propagate script kind to children
            parent = le.parent()
            if kind_str == InputKind.SCRIPT.value and isinstance(parent, ExpressionSlot):
                for le in parent.line_edits():
                    le.setProperty("LatexKind", InputKind.SCRIPT.value)

            min_pt = int(base_font * scale)
            scaled_max = int(max_pt * scale)

            apply_scaled_fonts(sample, [le], min_pt, scaled_max)
            update_autowidth(le)
