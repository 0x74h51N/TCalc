from __future__ import annotations

from collections import deque
from typing import Generator, Optional

import calc_native
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.ops import Operation, get_symbols_with_aliases
from tcalc.core.parser import tokenize
from tcalc.ui.components.math_primitives import ParenGlyph
from tcalc.ui.widgets.calc.config import display_config, font_scale_config
from tcalc.ui.widgets.calc.display.expression.expression_node import (
    ExpressionNode,
    ExpressionSlot,
    InputAlign,
    InputKind,
)
from tcalc.ui.widgets.calc.display.expression.widgets import (
    BraceWidget,
    BracketWidget,
    FractionWidget,
    ParenWidget,
    PowWidget,
    RootWidget,
    RoundParenWidget,
)
from tcalc.ui.widgets.utils import apply_scaled_fonts

from .utils import space_binary_ops, split_operand, update_autowidth


class Expression(QWidget):
    """Expression editor widget managing inputs and serialization for math-style UI."""

    plain_text_changed = Signal(str)
    input_created = Signal(object)

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

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._last_focused: QLineEdit | None = None
        self._rendering: bool = False

        self._inputs_layout = QVBoxLayout(self)
        self._inputs_layout.setContentsMargins(0, 0, 0, 0)
        self._inputs_layout.setSpacing(0)

        self._inputs_layout.addStretch(1)
        self._root = ExpressionSlot(
            self, kind=InputKind.MAIN, key=InputKind.MAIN.value, align=InputAlign.RIGHTT
        )
        self._inputs_layout.addWidget(self._root)
        self._inputs_layout.addStretch(1)

        self._last_focused = self._root.default_input()

        self._operator_symbol_values = get_symbols_with_aliases()
        self._operator_symbol_values.discard(Operation.IMAG.symbol)
        self._pending_seg: Optional[QLineEdit] = None
        self._pending_parens: dict[calc_native.ParenKind, list[ParenWidget]] = {}

        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.focusChanged.connect(self._on_app_focus_changed)

    #
    #
    #
    # ======================== Focus & Target Resolution ========================
    #

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

    #
    #
    #
    # ================== Text I/O (get / set / insert) ========================
    #

    def get_plain_text(self) -> str:
        return self._root.to_plain_text()

    def set_plain_text(self, text: str) -> None:
        le = self._root.reset()
        self._pending_parens.clear()
        self._last_focused = le
        le.setFocus()

        if le.text() == text:
            self.plain_text_changed.emit(self.get_plain_text())
            return
        le.setText(text)

    def insert_text(self, text: str) -> None:
        self._resolve_target().insert(text)

    #
    #
    #
    # ======================== Navigation ========================
    #

    def navigate_left(self) -> bool:
        return self._navigate_horizontal(-1)

    def navigate_right(self) -> bool:
        return self._navigate_horizontal(1)

    def navigate_up(self) -> bool:
        return self._navigate_vertical(-1)

    def navigate_down(self) -> bool:
        return self._navigate_vertical(1)

    def _iter_line_edits(
        self, start_seg: QLineEdit, direction: int
    ) -> Generator[QLineEdit, None, None]:
        """
        Iter line edits between parent widgets
        Direction: 1 (Forward/Right), -1 (Backward/Left)
        """
        current: QWidget = start_seg
        slot = start_seg.parent()

        while isinstance(slot, ExpressionSlot):
            segments = slot._segments
            idx = slot.index_of(current)

            indices = range(idx + 1, len(segments)) if direction > 0 else range(idx - 1, -1, -1)

            for i in indices:
                seg = segments[i]
                if isinstance(seg, QLineEdit):
                    yield seg
                elif isinstance(seg, ExpressionNode):
                    node_inputs = seg.line_edits()
                    if direction < 0:
                        node_inputs.reverse()
                    for le in node_inputs:
                        yield le

            node = slot.parent()
            if not isinstance(node, ExpressionNode):
                break
            current = node
            slot = node.parent()

    def _navigate_horizontal(self, direction: int) -> bool:
        """Move between segments horizontally, climbing the tree when needed."""
        target = self._resolve_target()
        at_edge = (
            target.cursorPosition() == 0
            if direction < 0
            else target.cursorPosition() >= len(target.text())
        )

        if not at_edge:
            return False

        nxt = next(self._iter_line_edits(target, direction), None)
        if nxt:
            nxt.setFocus()
            nxt.setCursorPosition(0 if direction > 0 else len(nxt.text()))
            return True
        return False

    def _navigate_vertical(self, direction: int) -> bool:
        """Climb the slot→node tree to find a vertical neighbor slot."""
        target = self._resolve_target()
        pos = target.cursorPosition()
        slot = target.parent()
        while isinstance(slot, ExpressionSlot):
            node = slot.parent()
            if not isinstance(node, ExpressionNode):
                break
            neighbor = node.slot_above(slot) if direction < 0 else node.slot_below(slot)
            if neighbor:
                le = neighbor.default_input()
                le.setFocus()
                le.setCursorPosition(min(pos, len(le.text())))
                return True
            slot = node.parent()
        return False

    #
    #
    #
    # ================== Key Handlers ==================
    #
    def backspace(self) -> None:
        """Handle backspace across slots/fractions when the current input is empty."""
        target = self._resolve_target()
        text = target.text()
        pos = target.cursorPosition()

        if pos and text[pos - 1] == " ":
            target.setCursorPosition(pos - 1)
            target.backspace()
            return

        slot = target.parent()
        if isinstance(slot, ExpressionSlot) and not pos and not text:
            node = slot.parent()
            if (
                isinstance(node, ExpressionNode)
                and slot is node._right_slot
                and len(slot._segments) == 1
            ):
                node.dissolve()
                self.plain_text_changed.emit(self.get_plain_text())
                return

        if isinstance(slot, ExpressionSlot) and not pos:
            idx = slot._segments.index(target)
            if idx > 0:
                prev = slot._segments[idx - 1]
                if isinstance(prev, ParenWidget):
                    prev.remove(prev._close_glyph)
                    self.plain_text_changed.emit(self.get_plain_text())
                    return
                if isinstance(prev, ParenGlyph):
                    slot.remove(prev)
                    self.plain_text_changed.emit(self.get_plain_text())
                    return
                if isinstance(prev, ExpressionNode):
                    self.navigate_left()
                    return
                if isinstance(prev, QLineEdit):
                    self._focus_backspace(prev)
                    return

        target.backspace()

    def _find_prev_line_edit(self, target: QLineEdit) -> QLineEdit | None:
        """Walk backwards through parent slot segments to find a QLineEdit before *target*.

        Skips over consecutive ExpressionNode segments finds the first last QLineEdit."""
        slot = target.parent()
        if not isinstance(slot, ExpressionSlot):
            return None
        segs = slot._segments
        try:
            idx = segs.index(target)
        except ValueError:
            return None
        for i in range(idx - 1, -1, -1):
            seg = segs[i]
            if isinstance(seg, QLineEdit):
                return seg
        return None

    def handle_negate(self) -> None:
        """Toggle unary minus for the operand at the cursor position."""
        target, prefix, suffix = self._split_target_at_cursor()
        minus = Operation.SUB.symbol

        # prefix empty: look at previous segments
        if not prefix:
            prev = self._find_prev_line_edit(target)
            if prev is not None:
                # Toggle minus at the end of the previous QLineEdit
                txt = prev.text()
                if txt.endswith(minus):
                    prev.setText(txt[: -len(minus)])
                else:
                    prev.setText(txt + minus)
                return
            # No previous segment — toggle bare minus in current target
            if suffix.startswith(minus):
                suffix = suffix[len(minus) :]
            else:
                suffix = minus + suffix
            target.setText(suffix)
            target.setCursorPosition(0 if suffix != minus else len(minus))
            return

        # bare minus only
        if prefix == minus and not suffix:
            target.setText("")
            target.setCursorPosition(0)
            return

        # tokenize prefix, find trailing operand
        toks = tokenize(prefix).tokens
        pre_toks, operand_toks = split_operand(toks)

        if operand_toks:
            op_start = operand_toks[0].start_pos
            # Check for existing unary minus right before the operand
            if (
                pre_toks
                and isinstance(pre_toks[-1].data, calc_native.OpToken)
                and pre_toks[-1].data.op_id == calc_native.OpId.Negate
            ):
                # Remove the negate
                new_prefix = prefix[: pre_toks[-1].start_pos] + prefix[op_start:]
            else:
                # Insert negate
                new_prefix = prefix[:op_start] + minus + prefix[op_start:]
        else:
            # No trailing operand — toggle minus at the start of suffix
            if suffix.startswith(minus):
                suffix = suffix[len(minus) :]
            else:
                suffix = minus + suffix
            new_prefix = prefix

        target.setText(new_prefix + suffix)
        target.setCursorPosition(len(new_prefix))

    def apply_key(self, label: str, op: Operation) -> None:
        """Insert operator text."""

        if op.arity == calc_native.OpArity.Unary:
            self.insert_text(f"{label}{Operation.OPEN_PAREN.symbol}")
            return

        op_id = getattr(op._spec, "id", None)
        self.insert_text(space_binary_ops(op_id, label))

    def insert_expr_str(self, expr_kind: calc_native.ExprKind) -> None:
        """Insert ExpressionNode via keystroke."""
        target = self._resolve_target()
        slot = target.parent()

        if not isinstance(slot, ExpressionSlot):
            return

        widget_cls = self.EXPR_KIND_MAP.get(expr_kind)
        if widget_cls is None:
            return

        # Insert empty expr at cursor, _add_exp_node handles split_operand
        text = target.text()
        cursor = target.cursorPosition()
        target.setText(
            text[:cursor] + calc_native.format_expr_str(expr_kind, "", "") + text[cursor:]
        )

        self.plain_text_changed.emit(self.get_plain_text())

    #
    #
    #
    # ================== Node Building (tokenize -> create widget -> insert) ==================
    #

    def _flush_exp_nodes(self):
        if self._pending_seg:
            self._add_exp_node(self._pending_seg)
            self.plain_text_changed.emit(self.get_plain_text())
            self._pending_seg = None

    def _on_input_changed(self, seg: QLineEdit):
        if self._rendering:
            return
        self._pending_seg = seg
        QTimer.singleShot(0, self._flush_exp_nodes)

    def _focus_backspace(self, le: QLineEdit) -> None:
        le.setFocus()
        le.setCursorPosition(len(le.text()))
        le.backspace()

    def _insert_node(
        self,
        slot: ExpressionSlot,
        seg: QLineEdit,
        prefix_tokens: list[calc_native.Token],
        node: ExpressionNode,
        suffix_tokens: list[calc_native.Token],
    ) -> QLineEdit:
        """Insert a node widget into slot: [prefix | node | suffix]."""
        idx = slot.index_of(seg)

        seg.setText(calc_native.tokens_to_text(prefix_tokens, self._seg_after_node(seg)))
        seg.setObjectName("prefix")
        slot.insert_widget(idx + 1, node)
        suffix_le = slot.insert_input(idx + 2)
        suffix_le.setText(calc_native.tokens_to_text(suffix_tokens, True))
        suffix_le.setObjectName("suffix")
        node.focus_default()
        return suffix_le

    def _seg_after_node(self, seg: QLineEdit) -> bool:
        """Check if the segment immediately follows an ExpressionNode in its slot."""
        slot = seg.parent()
        if not isinstance(slot, ExpressionSlot):
            return False
        idx = slot.index_of(seg)
        return idx > 0 and isinstance(slot._segments[idx - 1], ExpressionNode)

    def _normalize_text(self, seg: QLineEdit, tokens: list[calc_native.Token]) -> None:
        """Normalize text aliases to symbols (add -> + or floor -> ⌊)."""
        text = seg.text()
        new_text = calc_native.tokens_to_text(tokens, self._seg_after_node(seg))
        if new_text != text:
            cursor_pos = seg.cursorPosition()

            # Find new cursor by normalizing text before cursor
            # Tokens before/at cursor determine new position
            prefix_tokens = [t for t in tokens if t.start_pos < cursor_pos]

            new_cursor = len(calc_native.tokens_to_text(prefix_tokens))
            seg.setText(new_text)
            seg.setCursorPosition(min(new_cursor, len(new_text)))

    def _add_exp_node(self, changed: QLineEdit | None = None) -> None:
        self._rendering = True
        self.setUpdatesEnabled(False)
        dirty_inputs: set[QLineEdit] = set()

        try:
            if not changed:
                return
            pending: deque[QLineEdit] = deque([changed])

            while pending:
                seg = pending.popleft()
                parent = seg.parent()

                if not isinstance(parent, ExpressionSlot):
                    continue

                slot: ExpressionSlot = parent
                text = seg.text()

                if not text:
                    continue

                result = tokenize(text)
                tokens = result.tokens

                # Close-paren path: match against a pending open ParenWidget
                if not result.expr_indices and self._pending_parens:
                    if self._try_close_paren(seg, result):
                        continue

                if not result.expr_indices:
                    if self._try_wrap_adjacent(seg, slot, tokens):
                        pending.append(seg)
                        continue

                    if "\\" not in text:
                        self._normalize_text(seg, tokens)
                    continue

                no_match = calc_native.PAREN_NO_MATCH
                paren_first = result.open_paren_indices[0] if result.open_paren_indices else None
                expr_first = result.expr_indices[0]

                # Paren path: open paren before the first expr token
                # with a registered widget class in PAREN_KIND_MAP.
                open_paren_tok: calc_native.ParenToken | None = None
                paren_cls: type[ParenWidget] | None = None
                if (
                    paren_first is not None and paren_first < expr_first
                ):  # If paren start before LaTeX to cover it
                    _ptok = tokens[paren_first].as_paren()
                    paren_cls = self.PAREN_KIND_MAP.get(_ptok.kind)
                    if paren_cls is not None:
                        open_paren_tok = _ptok

                if open_paren_tok is not None and paren_cls is not None:
                    assert paren_first is not None
                    pair = open_paren_tok.pair_idx
                    has_close = pair != no_match

                    if has_close:
                        paren_end = pair + 1
                        close_tok = tokens[pair].as_paren()
                    else:
                        paren_end = len(tokens)
                        close_tok = None

                    prefix_tokens = tokens[:paren_first]
                    inner_tokens = tokens[paren_first + 1 : paren_end - (1 if has_close else 0)]
                    suffix_tokens = tokens[paren_end:] if has_close else []

                    paren_node = paren_cls(self, inner_tokens, open_paren_tok, close_tok)

                    if not has_close:
                        self._pending_parens.setdefault(open_paren_tok.kind, []).append(paren_node)

                    node: ExpressionNode = paren_node

                # Expr path: LaTeX expression (e.g. \frac, \pow)
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
                        return

                    node = widget_cls(self, left_tokens, right_tokens)

                suffix_seg = self._insert_node(slot, seg, prefix_tokens, node, suffix_tokens)
                dirty_inputs.update(node.line_edits())
                # Queue node's internal inputs for nested processing
                pending.extend(node.line_edits())

                if isinstance(suffix_seg, QLineEdit) and "\\" in suffix_seg.text():
                    pending.append(suffix_seg)

        finally:
            self.setUpdatesEnabled(True)
            self._rendering = False
            for le in dirty_inputs:
                update_autowidth(le)

    def _try_wrap_adjacent(
        self,
        seg: QLineEdit,
        slot: ExpressionSlot,
        tokens: list[calc_native.Token],
    ) -> bool:
        """Absorb right-hand siblings into *seg* when it ends with an open paren.

        Returns True if siblings were absorbed so the caller re-queues *seg*.
        """
        if not tokens:
            return False
        last = tokens[-1]

        if not isinstance(last.data, calc_native.ParenToken):
            return False
        if last.data.type != calc_native.ParenType.Open:
            return False

        # Reattach to a pending ParenWidget that lost its open glyph
        stack = self._pending_parens.get(last.data.kind)
        if stack:
            pw = stack.pop()
            if not stack:
                del self._pending_parens[last.data.kind]
            pw.set_open(last.data)
            seg.setText(calc_native.tokens_to_text(tokens[:-1]))
            return True

        seg_idx = slot.index_of(seg)
        right = slot._segments[seg_idx + 1 :]
        if not any(isinstance(s, ExpressionNode) for s in right):
            return False

        absorbed = slot.serialize_segments(right)
        slot.remove_segments(right)
        seg.setText(seg.text() + absorbed)
        return True

    def _try_close_paren(self, seg: QLineEdit, result: calc_native.TokenizeResult) -> bool:
        """Check if any token is a close paren that matches a pending open.

        If matched: close the ParenWidget, split the segment text around the paren,
        and move the trailing text to the next available input.
        """

        paren_ind = result.close_paren_indices
        tokens = result.tokens

        if not paren_ind:
            return False

        for idx in paren_ind:
            par = tokens[idx].as_paren()
            stack = self._pending_parens.get(par.kind)

            if par.type != calc_native.ParenType.Close or not stack:
                continue

            pw = stack.pop()
            if not stack:
                self._pending_parens.pop(par.kind)

            pw.set_close(par)

            before_text = calc_native.tokens_to_text(tokens[:idx], self._seg_after_node(seg))
            after_text = calc_native.tokens_to_text(tokens[idx + 1 :], True)

            seg.setText(before_text)

            suffix_seg = next(self._iter_line_edits(seg, 1), None)
            if suffix_seg:
                suffix_seg.setText(after_text + suffix_seg.text())

            return True
            # TODO: Add some tests about this func...

        return False

    #
    #
    #
    # ======================== Font Scaling ==============================
    #

    def update_input_fonts(self, sample: QWidget) -> None:
        """Update font and width of all inputs based on sample widget size."""
        base_font = int(display_config["expression_font_size"])

        for le in self.expression_inputs():
            kind_str = le.property("exprKind")
            scale = float(display_config.get(f"scale_{kind_str}", 1.0))

            # Propagate script kind to children
            parent = le.parent()
            if kind_str == InputKind.SCRIPT.value and isinstance(parent, ExpressionSlot):
                for le in parent.line_edits():
                    le.setProperty("exprKind", InputKind.SCRIPT.value)

            min_pt = int(base_font * scale)
            max_pt = int(font_scale_config["display_expression"]["max_pt"] * scale)

            apply_scaled_fonts(sample, [le], min_pt, max_pt)
            update_autowidth(le)
