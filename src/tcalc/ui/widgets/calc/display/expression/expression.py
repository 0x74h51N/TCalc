from __future__ import annotations

from collections import deque
from typing import Optional

import calc_native
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.ops import Operation, get_symbols_with_aliases
from tcalc.ui.widgets.calc.display.expression.expression_node import (
    ExpressionNode,
    ExpressionSlot,
    InputAlign,
    InputKind,
)
from tcalc.ui.widgets.calc.display.expression.widgets import FractionWidget, PowWidget

from .utils import (
    CLOSE_KIND,
    OPEN_KIND,
    space_binary_ops,
    split_operand,
    split_paren,
    token_text,
    tokens_to_text,
    untokenized_prefix,
)


class Expression(QWidget):
    """Expression editor widget managing inputs and serialization for math-style UI."""

    plain_text_changed = Signal(str)

    NODE_WIDGETS: dict[calc_native.OpId, type[ExpressionNode]] = {
        FractionWidget.OP_ID: FractionWidget,
        PowWidget.OP_ID: PowWidget,
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._last_focused: QLineEdit | None = None
        self._rendering: bool = False

        self._inputs_layout = QVBoxLayout(self)
        self._inputs_layout.setContentsMargins(0, 0, 0, 0)
        self._inputs_layout.setSpacing(0)

        self._inputs_layout.addStretch(1)
        self._root = ExpressionSlot(
            self, kind=InputKind.MAIN, key=InputKind.MAIN.value, align=InputAlign.RIGHT
        )
        self._inputs_layout.addWidget(self._root)
        self._inputs_layout.addStretch(1)

        self._last_focused = self._root.default_input()

        self._operator_symbol_values = get_symbols_with_aliases()
        self._operator_symbol_values.discard(Operation.IMAG.symbol)

        node_op_ids = set(self.NODE_WIDGETS.keys())
        self._node_op_syms: frozenset[str] = frozenset(
            get_symbols_with_aliases(lambda spec: getattr(spec, "id", None) in node_op_ids)
        )

        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.focusChanged.connect(self._on_app_focus_changed)

    def expression_inputs(self) -> list[QLineEdit]:
        return self._root.line_edits()

    def _on_app_focus_changed(self, _old, new) -> None:
        if isinstance(new, QLineEdit) and self.isAncestorOf(new):
            self._last_focused = new

    def _resolve_target(self) -> QLineEdit:
        """Return the input that should receive edits (focus or last focused)."""
        fw = QApplication.focusWidget()
        if isinstance(fw, QLineEdit) and self.isAncestorOf(fw):
            return fw
        if self._last_focused is not None and self.isAncestorOf(self._last_focused):
            return self._last_focused
        return self._root.default_input()

    def _split_target_at_cursor(self) -> tuple[QLineEdit, str, str]:
        """Return target input and its text split at the cursor position."""
        target = self._resolve_target()
        text = target.text()
        pos = target.cursorPosition()
        return target, text[:pos], text[pos:]

    def _on_qt_text_changed(self, _text: str) -> None:
        if not self._rendering:
            self._add_exp_node()
            self.plain_text_changed.emit(self.get_plain_text())

    def _analyze_tokens(
        self, tokens: list[calc_native.Token]
    ) -> tuple[bool, list[calc_native.Token], tuple[int, type[ExpressionNode]] | None]:
        """
        Single-pass: check wrapping and find node op at minimum depth.
        Returns: (is_wrapped, effective_tokens, (op_index, widget_class) or None)
        """
        if not tokens:
            return False, tokens, None

        potentially_wrapped = tokens[0].kind == OPEN_KIND and tokens[-1].kind == CLOSE_KIND

        depth = 0
        candidates = []  # (index, depth, op_id)
        wrapping_valid = True

        for i, tok in enumerate(tokens):
            if tok.kind == OPEN_KIND:
                depth += 1
            elif tok.kind == CLOSE_KIND:
                depth -= 1
                if potentially_wrapped and depth == 0 and i < len(tokens) - 1:
                    wrapping_valid = False
            elif tok.kind == calc_native.TokenKind.Op and tok.op_id in self.NODE_WIDGETS:
                candidates.append((i, depth, tok.op_id))

        is_wrapped = potentially_wrapped and wrapping_valid
        effective_tokens = tokens[1:-1] if is_wrapped else tokens

        if not candidates:
            return is_wrapped, effective_tokens, None

        # If wrapped, adjust index and depth for stripped outer paren
        if is_wrapped:
            candidates = [(i - 1, d - 1, op_id) for i, d, op_id in candidates]

        # Find candidate at minimum depth
        best = min(candidates, key=lambda x: (x[1], x[0]))
        return is_wrapped, effective_tokens, (best[0], self.NODE_WIDGETS[best[2]])

    def get_plain_text(self) -> str:
        return self._root.to_plain_text()

    def set_plain_text(self, text: str) -> None:
        le = self._root.reset()
        self._last_focused = le
        le.setFocus()

        if le.text() == text:
            self.plain_text_changed.emit(self.get_plain_text())
            return
        le.setText(text)

    def insert_text(self, text: str) -> None:
        self._resolve_target().insert(text)

    def backspace(self) -> None:
        """Handle backspace across slots/fractions when the current input is empty."""
        target = self._resolve_target()

        slot = target.parent()
        if isinstance(slot, ExpressionSlot):
            prev = slot._segments[slot._segments.index(target) - 1]
            if isinstance(prev, ExpressionNode):
                prev.remove()
                self.plain_text_changed.emit(self.get_plain_text())
                return

        target.backspace()

    def handle_negate(self) -> None:
        """Toggle unary minus for the current token sequence."""
        target, prefix, suffix = self._split_target_at_cursor()

        def apply_prefix(new_prefix: str) -> None:
            target.setText(new_prefix + suffix)
            target.setCursorPosition(len(new_prefix))

        if prefix in ("", Operation.SUB.symbol):
            apply_prefix("" if prefix else Operation.SUB.symbol)
            return

        toks = calc_native.tokenize_string(prefix)
        parts = [
            (t.op_id if t.kind == calc_native.TokenKind.Op else None, str(token_text(t)))
            for t in toks
        ]

        paren_split = split_paren(toks)
        paren_start = len(paren_split[0]) if paren_split else None
        for i in range(len(parts) - 1, -1, -1):
            txt = parts[i][1]

            if paren_start is not None and i > paren_start:
                continue
            if txt in self._operator_symbol_values and not (
                paren_start is not None and i == paren_start and txt == Operation.OPEN_PAREN.symbol
            ):
                continue

            unary_prev = (
                i > 0
                and parts[i - 1][1] == Operation.SUB.symbol
                and (i == 1 or parts[i - 2][1] in self._operator_symbol_values)
            )

            if unary_prev:
                parts.pop(i - 1)
            else:
                parts.insert(i, (calc_native.OpId.Negate, Operation.SUB.symbol))

            apply_prefix(space_binary_ops(parts))
            return

    def apply_key(self, label: str, op: Operation) -> None:
        """Insert operator text."""

        if op.arity == calc_native.OpArity.Unary:
            self.insert_text(f"{label}{Operation.OPEN_PAREN.symbol}")
            return

        op_id = getattr(op._spec, "id", None)
        self.insert_text(space_binary_ops([(op_id, label)]))

    def _focus_backspace(self, le: QLineEdit) -> None:
        le.setFocus()
        le.setCursorPosition(len(le.text()))
        le.backspace()

    def _insert_node(
        self,
        slot: ExpressionSlot,
        seg: QLineEdit,
        prefix: str,
        node: ExpressionNode,
        suffix_tokens: list[calc_native.Token],
    ) -> None:
        """Insert a node widget after the segment and handle prefix/suffix, in the correct slot."""
        idx = slot.index_of(seg)
        seg.setText(prefix)
        slot.insert_widget(idx + 1, node)

        suffix = tokens_to_text(suffix_tokens)
        right_idx = idx + 2

        if right_idx >= len(slot._segments):
            slot.append_input().setText(suffix)
        else:
            next_seg = slot._segments[right_idx]
            if isinstance(next_seg, QLineEdit):
                next_seg.setText(suffix + next_seg.text())
            else:
                slot.insert_input(right_idx).setText(suffix)

        node.focus_default()

    def _normalize_text(self, seg: QLineEdit, tokens: list[calc_native.Token]) -> None:
        """Normalize text aliases to symbols (add -> + or floor -> ⌊)."""
        text = seg.text()
        new_text = tokens_to_text(tokens)
        if new_text != text:
            cursor_pos = seg.cursorPosition()
            seg.setText(new_text)
            seg.setCursorPosition(min(cursor_pos + 1, len(new_text)))
            # TODO: implement better fix for the cursor bug, this still has an issue about text alias floo3.3 -> ⌊3.3

    def _add_exp_node(self) -> None:
        self._rendering = True
        self.setUpdatesEnabled(False)
        try:
            pending: deque[QLineEdit] = deque(self._root.line_edits())

            while pending:
                seg = pending.popleft()

                parent = seg.parent()
                if not isinstance(parent, ExpressionSlot):
                    continue
                slot: ExpressionSlot = parent

                text = seg.text()
                seg_tokens = calc_native.tokenize_string(text)

                # Early exit: no node op symbols
                if not any(s in text for s in self._node_op_syms):
                    self._normalize_text(seg, seg_tokens)
                    continue

                is_wrapped, seg_toks, found = self._analyze_tokens(seg_tokens)

                if not found:
                    continue

                inner_text = text[1:-1] if is_wrapped else text
                seg_prefix = untokenized_prefix(inner_text, seg_toks)

                op_idx, widget_class = found
                before_tokens = seg_toks[:op_idx]
                after_tokens = seg_toks[op_idx + 1 :]

                prefix_tokens, left_tokens = split_operand(before_tokens)
                right_tokens, suffix_tokens = split_operand(after_tokens, lead=True)

                node = widget_class(self, left_tokens, right_tokens)
                self._insert_node(
                    slot, seg, seg_prefix + tokens_to_text(prefix_tokens), node, suffix_tokens
                )

                # Queue node's internal line edits (numerator, denominator, etc.)
                pending.extend(node.line_edits())

                # Re-queue prefix segment if non-empty (might have nested operators in parens)
                if seg.text():
                    pending.append(seg)

                # Queue suffix segment if it exists
                node_idx = slot.index_of(node)
                if node_idx + 1 < len(slot._segments):
                    suffix_seg = slot._segments[node_idx + 1]
                    if isinstance(suffix_seg, QLineEdit):
                        pending.append(suffix_seg)
        finally:
            self.setUpdatesEnabled(True)
            self._rendering = False


# TODO: Implement proper tests
# Use Qt Test framework for UI interaction testing
#
# UI Interaction Tests:
# - Insert an ExpressionNode symbol middle of two number -> numbers should be split as left and right tokens and show in slots
# - Insert an ExpressionNode symbol non input -> left_tokens input area should be focues
# - Insert an ExpressionNode symbol after unary operation expression -> unary op expression should be in left_tokens slot
# - Insert an ExpressionNode into the middle of an existing expression as like 2+4+6 -> 4/ should be empty right_token slot (focused) FractionWidget
# - Modify different input slots after an ExpressionNode is added
# - Verify that the computed result and displayed expression update correctly
# - Test deletion, undo, and redo behavior for ExpressionNodes
# - Test cursor placement and focus handling when inserting operators
#
# Edge-case and complex expression tests:
# - Deeply nested expressions
# - Operator precedence and associativity
# - Unary operators (negative numbers)
# - Implicit multiplication cases
# - Division by zero and invalid expressions
# - Test correct parenthesification for entire ExpressionNode also left and right token slots
#
# problematic examples
# (2/(5/(4/(7/5))))
# ((1+2)*(3+4))/((5-6)/(7+8))
# 3+4*2/(1-5)^2^3
# 1+(2*(3+(4/(5-6))))
# ((-3)^2)/(2+(-1)*(4/2))
# 6/(2*(1+2))
# (((1/2)/(3/4))/(5/6))
# 12/(3+(4*(5-6/(7+8))))
# (3/4)+4/5
# (2/4)(3/4)
# ((1+(2/(3+(4/5+6))))*(7-(8/(9+10))))/((1+(2/(3+(4/5+6))))*(7-(8/(9+10))))
