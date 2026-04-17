#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from typing import Generator, Optional

import calc_native
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.ops import Operation
from tcalc.core.parser import tokenize
from tcalc.ui.config import calc_config
from tcalc.ui.widgets.math import (
    ExpressionNode,
    ExpressionSlot,
    FractionWidget,
    InputKind,
    MathRender,
    ParenWidget,
)
from tcalc.ui.widgets.math.math_primitives import ParenGlyph
from tcalc.ui.widgets.math.utils import split_operand
from tcalc.ui.widgets.utils import InputAlign

from .utils import space_binary_ops

_log = logging.getLogger("tcalc.ui.expression")


class Expression(QWidget):
    """Expression editor widget managing inputs and serialization for math-style UI."""

    plain_text_changed = Signal(str)
    input_created = Signal(object)
    focused_input_changed = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._last_focused: QLineEdit | None = None
        self.renderer = MathRender()
        self._inputs_layout = QVBoxLayout(self)
        self._inputs_layout.setContentsMargins(0, 0, 0, 0)
        self._inputs_layout.setSpacing(0)

        self._inputs_layout.addStretch(1)
        self._root = ExpressionSlot(
            kind=InputKind.MAIN, key=InputKind.MAIN.value, align=InputAlign.RIGHTT
        )
        self._root.editor = self
        self._inputs_layout.addWidget(self._root)
        self._inputs_layout.addStretch(1)

        self._last_focused = self._root.default_input()

        self._pending_seg: Optional[QLineEdit] = None
        self._restoring: bool = False
        self._pending_parens: dict[calc_native.ParenKind, list[ParenWidget]] = {}
        self.renderer.editor = self
        self.renderer.pending_parens = self._pending_parens

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
            self.focused_input_changed.emit(new)

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
        self._restoring = True
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
                    edits = seg._left_slot._direct_edits
                    yield edits[-1] if direction < 0 else edits[0]
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
        target = self._resolve_target()
        pos = target.cursorPosition()
        slot = target.parent()
        while isinstance(slot, ExpressionSlot):
            node = slot.parent()
            if not isinstance(node, ExpressionNode):
                break
            neighbor = node.slot_above(slot) if direction < 0 else node.slot_below(slot)
            if neighbor:
                # Descend through nested child nodes toward the target direction
                while neighbor._child_nodes:
                    child = neighbor._child_nodes[0]
                    entry = child._top_slot if direction > 0 else child._bottom_slot
                    if entry is None:
                        break
                    neighbor = entry
                le = neighbor._direct_edits[0]
                le.setFocus()
                if isinstance(slot.parent(), FractionWidget):
                    le.setCursorPosition(min(pos, len(le.text())))
                else:
                    le.setCursorPosition(len(le.text()))
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
            left = pos - 2
            if left > 0:
                start = left - (left > 0 and text[left - 1] == " ")
                target.setText(text[:start] + text[pos:])
                target.setCursorPosition(start)
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
                    edits = prev.line_edits()
                    if edits:
                        le = edits[-1]
                        le.setFocus()
                        le.setCursorPosition(len(le.text()))
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
            _log.debug("_find_prev_line_edit: target not found in segments")
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

        widget_cls = self.renderer.EXPR_KIND_MAP.get(expr_kind)
        if widget_cls is None:
            return

        # Insert empty expr at cursor, _add_exp_node handles split_operand
        text = target.text()
        cursor = target.cursorPosition()
        target.setText(
            text[:cursor] + calc_native.format_expr_str(expr_kind, "", "") + text[cursor:]
        )

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
        if self._restoring:
            self._restoring = False
            last = self._root.default_input()
            last.setFocus()
            last.setCursorPosition(len(last.text()))
            self._last_focused = last

    def _on_input_changed(self, seg: QLineEdit):
        if self.renderer.is_rendering:
            return
        self._pending_seg = seg
        QTimer.singleShot(0, self._flush_exp_nodes)

    def _register_input(self, le: QLineEdit) -> None:
        if le.property("_expr_connected"):
            return
        le.setProperty("_expr_connected", True)
        le.textChanged.connect(lambda _=None, seg=le: self._on_input_changed(seg))
        self.input_created.emit(le)

    def _focus_backspace(self, le: QLineEdit) -> None:
        le.setFocus()
        le.setCursorPosition(len(le.text()))
        le.backspace()

    def _add_exp_node(self, seg: QLineEdit) -> None:
        self.renderer.is_rendering = True
        try:
            parent = seg.parent()

            if not isinstance(parent, ExpressionSlot):
                return

            slot: ExpressionSlot = parent
            text = seg.text()

            if not text:
                return

            result = tokenize(text)
            tokens = result.tokens

            # Close-paren path: match against a pending open ParenWidget
            if not result.expr_indices and self._pending_parens:
                if self._try_close_paren(seg, result, slot):
                    return

            if not result.expr_indices:
                if self._try_open_paren(seg, result, slot):
                    return
                if "\\" not in text:
                    self.renderer.normalize_text(seg, tokens)
                return

            self.renderer.render_node(seg, result)

        except Exception:
            _log.debug("_add_exp_node failed", exc_info=True)
        finally:
            self.renderer.is_rendering = False

    def _try_open_paren(
        self,
        seg: QLineEdit,
        result: calc_native.TokenizeResult,
        slot: ExpressionSlot,
    ) -> bool:
        """Check if any token is an open paren with right-hand ExpressionNodes.

        If matched: create a ParenWidget, split the segment text around the paren,
        and absorb the trailing siblings into the new node.
        """
        if not result.open_paren_indices:
            return False

        tokens = result.tokens

        idx = result.open_paren_indices[-1]
        par = tokens[idx].as_paren()
        if par.type != calc_native.ParenType.Open or par.pair_idx != calc_native.PAREN_NO_MATCH:
            return False

        paren_cls = self.renderer.PAREN_KIND_MAP.get(par.kind)
        if paren_cls is None:
            return False

        before_toks, after_toks, detached = self._split_seg(seg, tokens, idx, slot)
        if not detached:
            return False

        paren_node = paren_cls(par, None)
        paren_node.editor = self
        paren_node.slot.default_input().setText(calc_native.tokens_to_text(after_toks))
        self._pending_parens.setdefault(par.kind, []).append(paren_node)

        paren_node.adopt_segments(detached)

        self.renderer.insert_node(slot, seg, before_toks, paren_node, False)
        line_edits = paren_node.slot.line_edits()
        if line_edits:
            le = line_edits[0]
            le.setFocus()
            le.setCursorPosition(0)
        return True

    def _try_close_paren(
        self,
        seg: QLineEdit,
        result: calc_native.TokenizeResult,
        slot: ExpressionSlot,
    ) -> bool:
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

            pw = stack[-1]
            if slot is not pw.slot:
                # Pre-check, only pop pending paren and attach when the close paren is in the inner slot.
                continue

            stack.pop()
            if not stack:
                self._pending_parens.pop(par.kind)

            before_toks, after_toks, detached = self._split_seg(seg, tokens, idx, slot)

            before_text = calc_native.tokens_to_text(before_toks, self.renderer.seg_after_node(seg))
            after_text = calc_native.tokens_to_text(after_toks)

            pw.set_close(par)
            seg.setText(before_text)

            before_result = calc_native.classify_tokens(before_toks)
            self.renderer.render_node(seg, before_result)
            suffix_seg = next(self._iter_line_edits(seg, 1), None)

            pw_parent = pw.parent()
            if isinstance(pw_parent, ExpressionSlot):
                if suffix_seg is None or suffix_seg.parent() is not pw_parent:
                    suffix_seg = pw_parent.insert_input(pw_parent.index_of(pw) + 1)

            if suffix_seg:
                suffix_seg.setText(after_text + suffix_seg.text())
                suffix_seg.setFocus()
                suffix_seg.setCursorPosition(0)

                if detached:
                    parent_slot = suffix_seg.parent()
                    if isinstance(parent_slot, ExpressionSlot):
                        parent_slot.adopt_segments(detached)

            if not pw.slot._child_nodes:
                pw.dissolve()

            return True

        return False

    def _split_seg(self, seg, tokens, idx, slot):
        before_toks = tokens[:idx]
        after_toks = tokens[idx + 1 :]
        detached: list[QWidget] = []
        seg_idx = slot.index_of(seg)
        seg_idx = slot.index_of(seg)
        has_node_right = bool(slot._child_nodes) and slot.index_of(slot._child_nodes[-1]) > seg_idx
        if has_node_right:
            detached = slot.detach_right_of(seg)
            if detached and isinstance(detached[-1], ParenGlyph):
                slot.insert_widget(len(slot._segments), detached.pop())
        return (before_toks, after_toks, detached)

    #
    #
    #
    # ======================== Font Scaling ==============================
    #

    def update_input_fonts(self, sample: QWidget) -> None:
        """Update font and width of all inputs based on sample widget size."""
        base_font = int(calc_config["display"]["expression_font_size"])
        max_pt = int(calc_config["display"]["expr_max_pt"])
        self.renderer.update_line_fonts(
            self.expression_inputs(), sample, base_font, max_pt, calc_config["display"]
        )
