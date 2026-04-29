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
        slot.insert_widget(idx + 1, node)
        if suffix:
            return slot.insert_input(idx + 2)
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

    def _build_paren(self, paren_kind: calc_native.ParenKind, has_close: bool) -> ExpressionNode:
        paren_cls = self.PAREN_KIND_MAP[paren_kind]

        open_tok = calc_native.ParenToken(calc_native.ParenType.Open, paren_kind)
        close_tok = (
            calc_native.ParenToken(calc_native.ParenType.Close, paren_kind) if has_close else None
        )
        widget = paren_cls(open_tok, close_tok)
        if not has_close:
            self._pending_parens.setdefault(paren_kind, []).append(widget)
        return widget

    def _render_all(
        self,
        seg: QLineEdit,
        nodes: list[tuple],
        dirty_inputs: set[QLineEdit],
    ) -> ExpressionNode | None:
        if not isValid(seg):
            return None
        slot = seg.parent()
        if not isinstance(slot, ExpressionSlot):
            return None
        return self._render_row(slot, seg, slot.index_of(seg), nodes, dirty_inputs)

    def _render_row(
        self,
        slot: ExpressionSlot,
        seg: QLineEdit,
        idx: int,
        nodes: list[tuple],
        dirty_inputs: set[QLineEdit],
    ) -> ExpressionNode | None:
        TEXT = calc_native.MATH_TAG_TEXT
        PAREN = calc_native.MATH_TAG_PAREN
        cur_seg = seg
        cur_idx = idx
        cur_seg.setText("")
        dirty_inputs.add(cur_seg)
        focus_target: ExpressionNode | None = None

        for node in nodes:
            kind = node[0]
            if kind == TEXT:
                cur_seg.setText(node[1])
                dirty_inputs.add(cur_seg)
                continue

            widget: ExpressionNode
            left_nodes: list[tuple] | None
            right_nodes: list[tuple] | None
            if kind == PAREN:
                _, paren_kind, has_close, paren_children = node
                widget = self._build_paren(paren_kind, has_close)
                tail_needed = has_close
                left_nodes, right_nodes = paren_children, None
            else:
                _, latex_kind, left_nodes, right_nodes = node
                widget_cls = self.LATEX_KIND_MAP[latex_kind]
                widget = widget_cls()
                tail_needed = True

            if not self._read_only:
                widget.editor = self.editor

            dirty_inputs.update(widget.line_edits())
            focus_target = widget

            if left_nodes:
                ls = widget._left_slot
                ls_seg = ls.default_input()
                focus_target = (
                    self._render_row(ls, ls_seg, ls.index_of(ls_seg), left_nodes, dirty_inputs)
                    or focus_target
                )
            if widget._right_slot and right_nodes:
                rs = widget._right_slot
                rs_seg = rs.default_input()
                focus_target = (
                    self._render_row(rs, rs_seg, rs.index_of(rs_seg), right_nodes, dirty_inputs)
                    or focus_target
                )

            slot.insert_widget(cur_idx + 1, widget)

            if not tail_needed:
                return focus_target
            cur_seg = slot.insert_input(cur_idx + 2)
            dirty_inputs.add(cur_seg)
            cur_idx += 2

        return focus_target

    def render_node(self, seg, tokenized: calc_native.TokensBranch) -> None:
        dirty_inputs: set[QLineEdit] = set()
        try:
            nodes = calc_native.build_math_nodes(tokenized, self.seg_after_node(seg))
            focus_target = self._render_all(seg, nodes, dirty_inputs)

            if not self._read_only and focus_target:
                focus_target.focus_default()

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
