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
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLineEdit,
    QWidget,
)
from shiboken6 import isValid

from tcalc.ui.widgets.math.expression_node import ExpressionNode, ExpressionSlot
from tcalc.ui.widgets.math.widgets import (
    BraceWidget,
    BracketWidget,
    FractionWidget,
    ParenWidget,
    PowWidget,
    RootWidget,
    RoundParenWidget,
)

from .utils import split_operand, update_autowidth

if TYPE_CHECKING:
    from tcalc.ui.widgets.calc.display.expression.expression import Expression


_log = logging.getLogger("tcalc.ui.math")


class MathRender(QWidget):
    rendering = Signal(bool)
    EXPR_KIND_MAP: dict[calc_native.ExprKind, type[ExpressionNode]] = {
        FractionWidget.EXPR_KIND: FractionWidget,
        PowWidget.EXPR_KIND: PowWidget,
        RootWidget.EXPR_KIND: RootWidget,
    }

    PAREN_KIND_MAP: dict[calc_native.ParenKind, type[ParenWidget]] = {
        BraceWidget.PAREN_KIND: BraceWidget,
        RoundParenWidget.PAREN_KIND: RoundParenWidget,
        BracketWidget.PAREN_KIND: BracketWidget,
    }

    def __init__(self) -> None:
        super().__init__()
        self._rendering: bool = False
        self._editor: Expression
        self._pending_parens: dict[calc_native.ParenKind, list[ParenWidget]]

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

    def _insert_node(
        self,
        slot: ExpressionSlot,
        seg: QLineEdit,
        prefix_tokens: list[calc_native.Token],
        node: ExpressionNode,
        suffix_tokens: list[calc_native.Token],
        suffix: bool = True,
    ) -> QLineEdit | None:
        """Insert a node widget into slot: [prefix | node | suffix]."""

        idx = slot.index_of(seg)

        seg.setText(calc_native.tokens_to_text(prefix_tokens, self._seg_after_node(seg)))
        seg.setObjectName("prefix")
        slot.insert_widget(idx + 1, node)
        if suffix:
            suffix_le = slot.insert_input(idx + 2)
            suffix_le.setText(calc_native.tokens_to_text(suffix_tokens, True))
            suffix_le.setObjectName("suffix")
            node.focus_default()
            return suffix_le
        return None

    def _seg_after_node(self, seg: QLineEdit) -> bool:
        """Check if the segment immediately follows an ExpressionNode in its slot."""
        slot = seg.parent()
        if not isinstance(slot, ExpressionSlot):
            return False
        idx = slot.index_of(seg)
        return idx > 0 and isinstance(slot._segments[idx - 1], ExpressionNode)

    def normalize_text(self, seg: QLineEdit, tokens: list[calc_native.Token]) -> None:
        """Normalize text aliases to symbols (add -> + or floor -> ⌊)."""
        text = seg.text()
        new_text = calc_native.tokens_to_text(tokens, self._seg_after_node(seg))
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
        pending: deque[tuple[QLineEdit, calc_native.TokenizeResult]],
    ) -> QLineEdit | None:

        if target is None or not tokens:
            return None

        classified = calc_native.classify_tokens(tokens)

        if classified.expr_indices or classified.open_paren_indices:
            pending.append((target, classified))
        else:
            target.setText(calc_native.tokens_to_text(tokens))

        return target

    def render_node(self, seg, tokenized: calc_native.TokenizeResult) -> None:
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

                tokens = tokenized.tokens
                if not tokenized.expr_indices:
                    continue

                no_match = calc_native.PAREN_NO_MATCH

                expr_first = tokenized.expr_indices[0]
                left_tokens: list[calc_native.Token] = []
                right_tokens: list[calc_native.Token] = []

                candidate = None

                # Paren path: open paren before the first expr token
                # with a registered widget class in PAREN_KIND_MAP.
                # This flow works for paren and latex expression render at same time
                # Otherwise parentheses catch by _try_open_paren and _try_close_paren
                for ind in tokenized.open_paren_indices:
                    if ind >= expr_first:
                        continue

                    pair_idx = tokens[ind].as_paren().pair_idx

                    # 1) unmatched "("
                    if pair_idx == no_match:
                        candidate = ind
                        break

                    # 2) matched "(" and close after expr start
                    if pair_idx > expr_first:
                        candidate = ind
                        break

                open_paren_tok: calc_native.ParenToken | None = None
                paren_cls: type[ParenWidget] | None = None

                if candidate is not None:
                    _ptok = tokens[candidate].as_paren()
                    paren_cls = self.PAREN_KIND_MAP.get(_ptok.kind)
                    if paren_cls is not None:
                        open_paren_tok = _ptok

                if open_paren_tok is not None and paren_cls is not None and candidate is not None:
                    pair = open_paren_tok.pair_idx
                    has_close = pair != no_match

                    if has_close:
                        paren_end = pair + 1
                        close_tok = tokens[pair].as_paren()
                    else:
                        paren_end = len(tokens)
                        close_tok = None

                    prefix_tokens = tokens[:candidate]
                    left_tokens = tokens[candidate + 1 : paren_end - (1 if has_close else 0)]
                    suffix_tokens = tokens[paren_end:] if has_close else []

                    paren_node = paren_cls(open_paren_tok, close_tok)
                    node: ExpressionNode = paren_node
                    suffix = has_close

                    if not has_close:
                        self._pending_parens.setdefault(open_paren_tok.kind, []).append(paren_node)

                    node.editor = self.editor

                else:
                    idx = expr_first
                    expr_tok = tokens[idx].as_expr()
                    before_tokens = tokens[:idx]
                    after_tokens = tokens[idx + 1 :]

                    # If expr has content (pasted), use it; otherwise split from surrounding tokens
                    if expr_tok.left:
                        prefix_tokens, left_tokens = before_tokens, expr_tok.left
                    else:
                        prefix_tokens, left_tokens = split_operand(before_tokens)

                    if expr_tok.right:
                        right_tokens, suffix_tokens = expr_tok.right, after_tokens
                    else:
                        right_tokens, suffix_tokens = split_operand(
                            after_tokens, lead=True, base_offset=idx + 1
                        )

                    widget_cls = self.EXPR_KIND_MAP.get(expr_tok.kind)

                    if widget_cls is None:
                        _log.debug("render_node: no widget for kind=%s", expr_tok.kind.name)
                        return

                    node = widget_cls()
                    node.editor = self.editor
                    suffix = True

                suffix_seg = self._insert_node(
                    slot, seg, prefix_tokens, node, suffix_tokens, suffix
                )

                # Populate widget slots with token text
                if node._left_slot:
                    self._queue(node._left_slot.default_input(), left_tokens, pending)
                if node._right_slot:
                    self._queue(node._right_slot.default_input(), right_tokens, pending)

                dirty_inputs.update(node.line_edits())

                # Enqueue suffix if it contains latex expressions
                if suffix_seg is not None and suffix_tokens:
                    self._queue(suffix_seg, suffix_tokens, pending)

        except Exception:
            _log.debug("_add_exp_node failed", exc_info=True)
        finally:
            for le in dirty_inputs:
                update_autowidth(le)
