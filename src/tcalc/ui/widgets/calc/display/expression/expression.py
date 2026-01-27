from __future__ import annotations

from typing import Optional

import calc_native
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.ops import Operation, get_symbols_with_aliases
from tcalc.ui.widgets.calc.config import display_config
from tcalc.ui.widgets.calc.display.expression.expression_node import (
    ExpressionNode,
    ExpressionSlot,
    InputAlign,
    InputKind,
)
from tcalc.ui.widgets.calc.display.expression.widgets import FractionWidget

from .utils import (
    CLOSE_KIND,
    OPEN_KIND,
    space_binary_ops,
    split_operand,
    split_paren,
    token_text,
    tokens_to_text,
    untokenized_prefix,
    update_autowidth,
    wrapped_in_parens,
)


class Expression(QWidget):
    """Expression editor widget managing inputs and serialization for math-style UI."""

    plain_text_changed = Signal(str)

    EXPR_PREFIX = "displayExpression_"

    NODE_WIDGETS: dict[calc_native.OpId, type[ExpressionNode]] = {
        FractionWidget.OP_ID: FractionWidget,
        # PowWidget.OP_ID: PowWidget,  # coming soon
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

        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.focusChanged.connect(self._on_app_focus_changed)

    def expression_inputs(self) -> list[QLineEdit]:
        return self._root.line_edits()

    def _create_input(
        self, key: str, *, kind: InputKind, align: InputAlign, parent: QWidget
    ) -> QLineEdit:
        le = QLineEdit("", parent)
        le.setObjectName(f"{self.EXPR_PREFIX}{key}")
        le.setAlignment(align.value)
        le.setProperty("exprInput", True)
        le.setProperty("exprKind", kind.value)

        base_pt = int(display_config["expression_font_size"])
        if kind != InputKind.MAIN:
            base_pt = max(8, int(base_pt * 0.7))

        f = QFont()
        f.setPointSize(base_pt)
        le.setFont(f)

        le.textChanged.connect(self._on_qt_text_changed)
        le.textChanged.connect(lambda _text, le=le: update_autowidth(le))
        QTimer.singleShot(0, lambda: update_autowidth(le))
        return le

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

    def _find_node_op(
        self, tokens: list[calc_native.Token]
    ) -> tuple[int, type[ExpressionNode]] | None:
        """Find first operator that triggers a node widget. Returns (index, widget_class)."""
        candidates: list[tuple[int, int]] = []  # (index, depth)
        depth = 0
        for i, token in enumerate(tokens):
            if token.kind == OPEN_KIND:
                depth += 1
                continue
            if token.kind == CLOSE_KIND:
                depth = max(0, depth - 1)
                continue
            if token.kind == calc_native.TokenKind.Op and token.op_id in self.NODE_WIDGETS:
                candidates.append((i, depth))

        if not candidates:
            return None

        best = min(candidates, key=lambda x: (x[1], x[0]))
        return best[0], self.NODE_WIDGETS[tokens[best[0]].op_id]

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
        suffix_tokens: list[calc_native.Token] | str,
    ) -> None:
        """Insert a node widget after the segment and handle prefix/suffix, in the correct slot."""
        idx = slot.index_of(seg)
        seg.setText(prefix)

        slot.insert_widget(idx + 1, node)

        if suffix_tokens:
            if isinstance(suffix_tokens, str):
                suffix = suffix_tokens
            else:
                suffix = tokens_to_text(suffix_tokens)
            if idx + 2 < len(slot._segments):
                next_seg = slot._segments[idx + 2]
                if isinstance(next_seg, QLineEdit):
                    next_seg.setText(suffix + next_seg.text())
            else:
                slot.append_input().setText(suffix)
        elif idx + 1 == len(slot._segments) - 1:
            slot.append_input()

        node.focus_default()
        self.plain_text_changed.emit(self.get_plain_text())

    def _add_exp_node(self) -> None:
        self._rendering = True
        try:
            while True:  # Nested ExpressionNode conversion loop
                changed = False
                for seg in self._root.line_edits():
                    parent = seg.parent()
                    if not isinstance(parent, ExpressionSlot):
                        continue
                    slot: ExpressionSlot = parent

                    text = seg.text()

                    seg_tokens = calc_native.tokenize_string(text)
                    is_wrapped = wrapped_in_parens(seg_tokens)
                    seg_toks = seg_tokens[1:-1] if is_wrapped else seg_tokens
                    inner_text = text[1:-1] if is_wrapped else text

                    seg_prefix = untokenized_prefix(inner_text, seg_toks)

                    found = self._find_node_op(seg_toks)
                    if not found:
                        continue

                    op_idx, widget_class = found
                    before_tokens = seg_toks[:op_idx]
                    after_tokens = seg_toks[op_idx + 1 :]
                    prefix_tokens, left_tokens = split_operand(before_tokens)

                    # detect raw leading '+'/'-' before the first after-token
                    # otherwise tokenization makes this unary plus/minus
                    leading_sign = ""
                    if after_tokens:
                        pref = untokenized_prefix(inner_text, after_tokens).strip()
                        if pref and pref[-1] in [Operation.ADD.symbol, Operation.SUB.symbol]:
                            leading_sign = pref[-1]

                    right_tokens: list[calc_native.Token] | None = None
                    suffix_tokens: list[calc_native.Token] | str
                    if leading_sign:
                        suffix_tokens = leading_sign + tokens_to_text(after_tokens)
                    else:
                        right_tokens, suffix_tokens = split_operand(after_tokens, lead=True)

                    node = widget_class(self, left_tokens, right_tokens)
                    self._insert_node(
                        slot, seg, seg_prefix + tokens_to_text(prefix_tokens), node, suffix_tokens
                    )
                    changed = True
                    break
                if not changed:
                    break
        finally:
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
# (2/4)(3/4)
# (1+(2/(3+(4/(5+6)))))*(7-(8/(9+10)))
