#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING, Callable, ClassVar

import calc_native
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QWidget,
)
from shiboken6 import isValid

from tcalc.ui.widgets.utils import InputAlign

from ..math_primitives import ParenGlyph
from ..utils import update_autowidth

_log = logging.getLogger("tcalc.ui.expression_node")


if TYPE_CHECKING:
    from tcalc.ui.widgets.calc.display.expression.expression import Expression


class InputKind(Enum):
    """Tag inputs as main expression or auxiliary slots."""

    MAIN = "main"
    AUX = "aux"
    SCRIPT = "script"


class ExpressionNode(QWidget):
    """Base class for math expression widgets that can serialize to text."""

    def __init__(
        self,
    ):
        super().__init__()
        self._editor: Expression | None = None

        self._left_slot: ExpressionSlot
        self._right_slot: ExpressionSlot | None = None
        self._top_slot: ExpressionSlot | None = None
        self._bottom_slot: ExpressionSlot | None = None

    OP_ID: ClassVar[calc_native.OpId]
    LATEX_KIND: ClassVar[calc_native.LatexKind]
    SYMBOL: ClassVar[str | None] = None

    @property
    def editor(self) -> Expression:
        if self._editor is None:
            raise RuntimeError("ExpressionNode editor is not set")
        return self._editor

    @editor.setter
    def editor(self, editor: Expression) -> None:
        self._editor = editor
        for slot in (self._left_slot, self._right_slot, self._top_slot, self._bottom_slot):
            if isinstance(slot, ExpressionSlot):
                slot.editor = editor

    def anchor_y(self) -> int:
        return (self.height() - self.contentsMargins().top()) // 2

    def line_edits(self) -> list[QLineEdit]:
        out = []
        if self._left_slot:
            out.extend(self._left_slot.line_edits())
        if self._right_slot:
            out.extend(self._right_slot.line_edits())
        return out

    def to_plain_text(self) -> str:
        """Serialize to LaTeX-style format: \\symbol{left}{right}."""
        # unary / paren node
        if not self.SYMBOL:
            return self._left_slot.to_plain_text()

        # binary node
        if self._left_slot is None or self._right_slot is None:
            return ""

        return calc_native.format_expr_str(
            self.LATEX_KIND,
            self._left_slot.to_plain_text(),
            self._right_slot.to_plain_text(),
        )

    def focus_default(self) -> None:
        """Focus the default input after widget creation."""
        slot = self._right_slot or self._left_slot
        if slot:
            slot.default_input().setFocus()

    def slot_above(self, current: ExpressionSlot) -> ExpressionSlot | None:
        return self._top_slot if current is self._bottom_slot else None

    def slot_below(self, current: ExpressionSlot) -> ExpressionSlot | None:
        return self._bottom_slot if current is self._top_slot else None

    def _resolve_focus(self, *fallbacks: ExpressionSlot) -> QLineEdit:
        """Return _last_focused if valid, otherwise first fallback's default_input."""
        editor = self._editor
        if editor is not None:
            f = editor._last_focused
            if f is not None and isinstance(f, QLineEdit) and isValid(f):
                return f
            if not fallbacks:
                return editor._root.default_input()

        if fallbacks:
            return fallbacks[0].default_input()

        raise RuntimeError("No focus target available")

    @staticmethod
    def _write_back_at_cursor(focus: QLineEdit, text: str, cursor_offset: int) -> None:
        """Insert *text* into *focus* at the current cursor position."""
        cur = focus.cursorPosition()
        before = focus.text()[:cur]
        after = focus.text()[cur:]
        focus.setText(before + text + after)
        focus.setCursorPosition(cur + cursor_offset)

    def dissolve(self) -> None:
        """Dissolve this node: move _left_slot segments into parent slot."""
        from .widgets import ParenWidget

        parent = self.parent()
        if not isinstance(parent, ExpressionSlot):
            return

        if self._left_slot and self._left_slot._child_nodes:
            segments = list(self._left_slot._segments)
            self._left_slot.remove_segments(segments, delete=False)
            focus = parent.replace_with(self, segments)
        else:
            plain = self._left_slot.to_plain_text() if self._left_slot else ""
            parent.remove(self)
            focus = self._resolve_focus(parent)
            self._write_back_at_cursor(focus, plain, len(plain))

        # Cascade: dissolve ancestor ParenWidgets with no ExpressionNode children.
        while True:
            slot = focus.parent() if isValid(focus) else None
            if not isinstance(slot, ExpressionSlot):
                break
            paren = slot.parent()
            if not isinstance(paren, ParenWidget):
                break
            if slot._child_nodes:
                break

            plain = paren.to_plain_text()
            cursor_in_paren = focus.cursorPosition() if isValid(focus) else 0
            open_len = len(paren._open_token.symbol) if paren._open_token else 0

            # Ensure suffix QLineEdit exists for unclosed parens
            paren_slot = paren.parent()
            if isinstance(paren_slot, ExpressionSlot):
                pidx = paren_slot.index_of(paren)
                has_right = pidx + 1 < len(paren_slot._segments) and isinstance(
                    paren_slot._segments[pidx + 1], QLineEdit
                )
                if not has_right:
                    paren_slot.insert_input(pidx + 1)

                paren._dissolve(False)

                focus = self._resolve_focus(paren_slot, parent)
                self._write_back_at_cursor(focus, plain, open_len + cursor_in_paren)

    def remove(self) -> None:
        """Remove this node from its parent slot."""
        parent = self.parent()
        if isinstance(parent, ExpressionSlot):
            parent.remove(self)
        else:
            self.deleteLater()


class ExpressionSlot(QWidget):
    """A horizontal slot that holds inputs and nested expression nodes."""

    EXPR_PREFIX = "displayExpression_"

    def __init__(
        self,
        kind: InputKind,
        key: str,
        align: InputAlign,
        paren: tuple[str | None, str | None] | None = None,
    ) -> None:
        super().__init__()

        self._kind = kind
        self._key = key
        self._align = align
        self._paren = paren  # (open_symbol, close_symbol) or None
        self._editor: Expression | None = None
        self._segments: list[QWidget] = []
        self._direct_edits: list[QLineEdit] = []
        self._child_nodes: list[ExpressionNode] = []

        self.setProperty("exprSlot", True)
        self.setProperty("exprSlotKind", kind.value)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._layout = QHBoxLayout(self)

        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._layout.setAlignment(self._align.value)

        self.append_input()

        self._margin_scheduled = False
        self._suppress_margins = False
        self._on_node_removed: Callable[[], None] | None = None
        self._on_margin_updated: Callable[[], None] | None = None

    def _input_key(self) -> str:
        return f"{self._key}_{len(self._segments)}"

    @property
    def editor(self) -> Expression | None:
        return self._editor

    @editor.setter
    def editor(self, editor: Expression | None) -> None:
        self._editor = editor
        if self._editor is None:
            return
        for seg in self._segments:
            if isinstance(seg, QLineEdit):
                self._editor._register_input(seg)
            elif isinstance(seg, ExpressionNode):
                seg.editor = self._editor
            elif isinstance(seg, ExpressionSlot):
                seg.editor = self._editor

    def _run_autowidth(self, le: QLineEdit) -> None:
        try:
            le.setProperty("_aw_scheduled", False)
        except RuntimeError:
            _log.debug("_run_autowidth: widget already deleted")
            return
        update_autowidth(le)

    def schedule_autowidth(self, le: QLineEdit) -> None:
        if le.property("_aw_scheduled"):
            return
        le.setProperty("_aw_scheduled", True)
        QTimer.singleShot(0, lambda le=le: self._run_autowidth(le))

    def _create_input(self, key: str) -> QLineEdit:
        """Create a new QLineEdit with proper styling and connections."""
        le = QLineEdit("", self)
        le.setObjectName(f"{self.EXPR_PREFIX}{key}")
        le.setAlignment(self._align.value)
        le.setProperty("exprInput", True)
        le.setProperty("LatexKind", self._kind.value)
        if self._editor is not None:
            self._editor._register_input(le)
            QTimer.singleShot(0, lambda: self.schedule_autowidth(le))
        return le

    def append_input(self) -> QLineEdit:
        le = self._create_input(self._input_key())
        self._layout.addWidget(le, 0, self._align.value)
        self._segments.append(le)
        self._direct_edits.append(le)
        return le

    def insert_widget(self, index: int, w: QWidget) -> None:
        self._layout.insertWidget(index, w, 0, self._align.value)
        self._segments.insert(index, w)
        if isinstance(w, ExpressionNode):
            self._child_nodes.append(w)

    def insert_input(self, index: int) -> QLineEdit:
        le = self._create_input(self._input_key())
        self._layout.insertWidget(index, le, 0, self._align.value)
        self._segments.insert(index, le)
        self._direct_edits.append(le)
        return le

    def default_input(self) -> QLineEdit:
        if self._direct_edits:
            return self._direct_edits[-1]
        return self.append_input()

    def index_of(self, seg: QWidget) -> int:
        return self._segments.index(seg)

    def _remove_segment(self, seg: QWidget, delete: bool = True) -> None:
        if seg not in self._segments:
            return
        self._layout.removeWidget(seg)
        self._segments.remove(seg)
        if isinstance(seg, QLineEdit) and seg in self._direct_edits:
            self._direct_edits.remove(seg)
        elif isinstance(seg, ExpressionNode) and seg in self._child_nodes:
            self._child_nodes.remove(seg)
        if delete:
            seg.deleteLater()

    def _merge_edits(self, left: QLineEdit, right: QLineEdit) -> None:
        left.setText(left.text() + right.text())
        if right in self._segments:
            self._layout.removeWidget(right)
            self._segments.remove(right)
        if right in self._direct_edits:
            self._direct_edits.remove(right)
        right.deleteLater()

    def _splice(self, idx: int, segments: list[QWidget]) -> QLineEdit | None:
        """Insert *segments* at *idx*, merge adjacent QLineEdits."""
        left = self._segments[idx - 1] if idx > 0 else None
        right = self._segments[idx] if idx < len(self._segments) else None

        off = 0
        for w in segments:
            if isinstance(w, ParenGlyph):
                slot = w.parent()
                paren = slot._paren if isinstance(slot, ExpressionSlot) else None
                sym = (paren[0] if w._opening else paren[1]) if paren else None
                prev = self._segments[idx + off - 1] if idx + off > 0 else None
                if sym and isinstance(prev, QLineEdit):
                    prev.setText(prev.text() + sym)
                w.deleteLater()
                continue
            self._layout.insertWidget(idx + off, w, 0, self._align.value)
            self._segments.insert(idx + off, w)
            if isinstance(w, QLineEdit):
                self._direct_edits.append(w)
            elif isinstance(w, ExpressionNode):
                self._child_nodes.append(w)
            off += 1

        focus: QLineEdit | None = None
        first = (
            self._segments[idx]
            if idx < len(self._segments) and self._segments[idx] is not right
            else None
        )
        if isinstance(left, QLineEdit) and isinstance(first, QLineEdit):
            cursor = len(left.text())
            self._merge_edits(left, first)
            focus = left
            focus.setCursorPosition(cursor)

        # Merge last segment with right neighbor if both QLineEdit
        if right is not None and isinstance(right, QLineEdit):
            right_idx = self._segments.index(right)
            prev = self._segments[right_idx - 1] if right_idx > 0 else None
            if isinstance(prev, QLineEdit):
                self._merge_edits(prev, right)
                if focus is None:
                    focus = prev

        return focus

    #
    #
    # segment operations APIs

    def adopt_segments(self, segments: list[QWidget]) -> None:
        focus = self._splice(len(self._segments), segments)
        if focus is not None:
            focus.setFocus()

    def detach_right_of(self, seg: QWidget) -> list[QWidget]:
        idx = self.index_of(seg)
        right = self._segments[idx + 1 :]
        if not right:
            return []
        detached = list(right)
        self.remove_segments(right, False)
        return detached

    def remove_segments(self, segs: list[QWidget], delete: bool = True) -> None:
        """Remove a list of segments from this slot, optionally destroying each widget."""
        for s in reversed(segs):
            self._remove_segment(s, delete)

    def replace_with(self, node: QWidget, replacements: list[QWidget]) -> QLineEdit:
        """Replace *node* with *replacements*, merging adjacent QLineEdits.

        Returns the QLineEdit that received focus after merging.
        """
        idx = self._segments.index(node)
        self._remove_segment(node, delete=False)

        focus = self._splice(idx, replacements)

        if focus is None:
            focus = self.default_input()

        node.deleteLater()
        focus.setFocus()
        self._schedule_margin_update()
        if self._on_node_removed:
            self._on_node_removed()
        return focus

    def remove(self, seg: QWidget) -> None:
        if seg not in self._segments:
            return

        idx = self._segments.index(seg)

        left = self._segments[idx - 1] if idx > 0 else None

        # Paren glyph: delegate to the owning ParenWidget
        if isinstance(seg, ParenGlyph):
            from .widgets import ParenWidget

            node = self.parent()
            if isinstance(node, ParenWidget):
                node.remove(seg)
            return

        # If node with QLineEdit neighbors, merge them into one and remove node+right
        right = self._segments[idx + 1] if idx + 1 < len(self._segments) else None
        if isinstance(left, QLineEdit) and isinstance(right, QLineEdit):
            left_text = left.text()
            self._merge_edits(left, right)
            self._remove_segment(seg)
            left.setFocus()
            left.setCursorPosition(len(left_text))
            if self._on_node_removed:
                self._on_node_removed()
            return

        if isinstance(seg, QLineEdit):
            self._direct_edits.remove(seg)

        if self._on_node_removed:
            self._on_node_removed()

    def reset(self) -> QLineEdit:
        for seg in self._segments:
            self._layout.removeWidget(seg)
            seg.deleteLater()
        for le in self._direct_edits:
            self._layout.removeWidget(le)
            le.deleteLater()
        self._segments = []
        self._direct_edits = []
        self._child_nodes = []

        return self.append_input()

    def line_edits(self) -> list[QLineEdit]:
        out: list[QLineEdit] = []
        for seg in self._segments:
            if isinstance(seg, QLineEdit):
                out.append(seg)
            elif isinstance(seg, (ExpressionNode, ExpressionSlot)):
                out.extend(seg.line_edits())
        return out

    def to_plain_text(self) -> str:
        parts: list[str] = []
        for seg in self._segments:
            if isinstance(seg, QLineEdit):
                parts.append(seg.text())
            elif isinstance(seg, (ExpressionNode, ExpressionSlot)):
                parts.append(seg.to_plain_text())
        inner = "".join(parts)
        if self._paren is not None:
            open_par = self._paren[0] or ""
            close_par = self._paren[1] or ""
            return open_par + inner + close_par
        return inner

    @staticmethod
    def _seg_anchor(seg: QWidget) -> tuple[int, int] | None:
        """Return (above, below) anchor distances for a segment, or None."""
        if isinstance(seg, ExpressionNode):
            a = seg.anchor_y()
            b = seg.height() - seg.contentsMargins().top() - a
            return a, b
        if isinstance(seg, ExpressionSlot):
            top_margin = seg.contentsMargins().top()
            h = seg.height() - top_margin
            a = h // 2
            return a, h - a
        if isinstance(seg, QLineEdit):
            a = seg.fontMetrics().height() // 2
            return a, a
        return None

    def anchor_y(self) -> int:
        """Return the maximum anchor-above across all segments in this slot."""
        max_anchor = 0
        for seg in self._segments:
            ab = self._seg_anchor(seg)
            if ab is not None and ab[0] > max_anchor:
                max_anchor = ab[0]
        return max_anchor

    def _update_segment_margins(self) -> None:
        """
        Align all segments in this slot to a common anchor_y position.

        Each segment (QLineEdit or ExpressionNode) defines its own
        vertical reference position via anchor_y() or text midpoint.

        This method computes the maximum anchor_y among all segments
        and applies a top margin offset so that:

            own_anchor_y + top_margin == max_anchor_y

        This ensures that all segments share the same visual
        reference Y position inside the horizontal layout.
        """
        max_anchor = 0
        max_below = 0

        for seg in self._segments:
            ab = self._seg_anchor(seg)
            if ab is None:
                continue
            if ab[0] > max_anchor:
                max_anchor = ab[0]
            if ab[1] > max_below:
                max_below = ab[1]

        for seg in self._segments:
            ab = self._seg_anchor(seg)
            if ab is not None:
                own_anchor = ab[0]
                top = max(0, max_anchor - own_anchor)
                if isinstance(seg, ExpressionNode):
                    if seg.contentsMargins().top() != top:
                        seg.setContentsMargins(0, top, 0, 0)
                elif isinstance(seg, ExpressionSlot):
                    if seg.contentsMargins().top() != top:
                        seg.setContentsMargins(0, top, 0, 0)
                elif isinstance(seg, QLineEdit):
                    if seg.textMargins().top() != top:
                        seg.setTextMargins(0, top, 0, 0)
            elif isinstance(seg, ParenGlyph):
                seg.setFixedHeight(max_anchor + max_below + 2)

    def _schedule_margin_update(self) -> None:
        """Update margins after first frame render."""
        self.setUpdatesEnabled(False)
        if self._margin_scheduled:
            return
        self._margin_scheduled = True
        QTimer.singleShot(0, self._do_margin_update)

    def _do_margin_update(self) -> None:
        try:
            if not isValid(self):
                return
            self._update_segment_margins()
            self._margin_scheduled = False

            # Read-only slots have fixed fonts and content, so anchors never
            # change after the first margin pass. Self-freeze to skip any
            # future resize-driven cascade.
            self._suppress_margins = self.editor is None

            # Propagate margin child to parent
            node = self.parent()
            if isinstance(node, ExpressionNode):
                parent_slot = node.parent()
                if isinstance(parent_slot, ExpressionSlot):
                    parent_slot._schedule_margin_update()
                    return
        finally:
            if self._on_margin_updated is not None:
                self._on_margin_updated()
            if isValid(self):
                self.setUpdatesEnabled(True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._suppress_margins:
            return
        self._schedule_margin_update()
