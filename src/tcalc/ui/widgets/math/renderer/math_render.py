#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING

import calc_native
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLineEdit,
    QWidget,
)
from shiboken6 import isValid

from tcalc.ui.widgets.utils import apply_scaled_fonts

from ..utils import ExprSplit, ParenSplit, structural_split, update_autowidth
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

    def _queue(
        self,
        target: QLineEdit | None,
        tokens: list[calc_native.Token],
        pending: deque[tuple[QLineEdit, calc_native.TokensBranch]],
    ) -> QLineEdit | None:

        if target is None or not tokens:
            return None

        classified = calc_native.classify_tokens(tokens)

        if classified.latex_indices:
            pending.append((target, classified))
        else:
            target.setText(calc_native.tokens_to_text(tokens))

        return target

    def render_node(self, seg, tokenized: calc_native.TokensBranch) -> None:
        dirty_inputs: set[QLineEdit] = set()
        pending = deque([(seg, tokenized)])

        try:
            while pending:
                seg, tokenized = pending.popleft()
                if not isValid(seg):
                    continue
                parent = seg.parent()

                if not isinstance(parent, ExpressionSlot):
                    continue

                slot: ExpressionSlot = parent

                split = structural_split(tokenized)
                if split is None:
                    continue

                left_tokens: list[calc_native.Token] = []
                right_tokens: list[calc_native.Token] = []
                node: ExpressionNode

                if isinstance(split, ParenSplit):
                    paren_cls = self.PAREN_KIND_MAP.get(split.open_tok.kind)
                    if paren_cls is None:
                        _log.debug("render_node: no widget for paren kind=%s", split.open_tok.kind)
                        return

                    prefix_tokens = split.prefix
                    left_tokens = split.left
                    suffix_tokens = split.suffix

                    paren_node = paren_cls(split.open_tok, split.close_tok)
                    node = paren_node
                    suffix = split.has_close

                    if not split.has_close:
                        self._pending_parens.setdefault(split.open_tok.kind, []).append(paren_node)

                    if not self._read_only:
                        node.editor = self.editor
                else:
                    assert isinstance(split, ExprSplit)
                    prefix_tokens = split.prefix
                    left_tokens = split.left
                    right_tokens = split.right
                    suffix_tokens = split.suffix

                    widget_cls = self.LATEX_KIND_MAP.get(split.kind)
                    if widget_cls is None:
                        _log.debug("render_node: no widget for kind=%s", split.kind.name)
                        return

                    node = widget_cls()
                    if not self._read_only:
                        node.editor = self.editor
                    suffix = True

                suffix_seg = self.insert_node(slot, seg, prefix_tokens, node, suffix)

                # Populate widget slots with token text
                if node._left_slot:
                    self._queue(node._left_slot.default_input(), left_tokens, pending)
                if node._right_slot:
                    self._queue(node._right_slot.default_input(), right_tokens, pending)

                if not self._read_only:
                    node.focus_default()

                dirty_inputs.add(seg)
                dirty_inputs.update(node.line_edits())
                if suffix_seg is not None:
                    dirty_inputs.add(suffix_seg)

                # Enqueue suffix if it contains latex expressions
                if suffix_seg is not None and suffix_tokens:
                    self._queue(suffix_seg, suffix_tokens, pending)

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
