from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Callable, ClassVar

import calc_native
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QWidget,
)

from tcalc.ui.components.math_primitives import ParenGlyph

from .utils import format_expr_str, update_autowidth

if TYPE_CHECKING:
    from .expression import Expression


class InputKind(Enum):
    """Tag inputs as main expression or auxiliary slots."""

    MAIN = "main"
    AUX = "aux"
    SCRIPT = "script"


class InputAlign(Enum):
    """Predefined alignment flags for expression inputs (text alignment)."""

    LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    CENTER = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
    RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    RIGHTB = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom
    LEFTB = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
    RIGHTT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
    LEFTT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
    BOTTOM = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
    TOP = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop


class ExpressionNode(QWidget):
    """Base class for math expression widgets that can serialize to text."""

    def __init__(
        self,
        editor: Expression,
        left_tokens: list[calc_native.Token] | None,
        right_tokens: list[calc_native.Token] | None,
    ):
        super().__init__(editor)
        self._editor = editor
        self.left_tokens = left_tokens if left_tokens is not None else []
        self.right_tokens = right_tokens if right_tokens is not None else []

        self._left_slot: ExpressionSlot | None = None
        self._right_slot: ExpressionSlot | None = None
        self._top_slot: ExpressionSlot | None = None
        self._bottom_slot: ExpressionSlot | None = None

    OP_ID: ClassVar[calc_native.OpId]
    EXPR_KIND: ClassVar[calc_native.ExprKind]
    SYMBOL: ClassVar[str | None] = None

    def anchor_y(self) -> int:
        return self.height() // 2

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
            if self._left_slot is None:
                return ""
            return self._left_slot.to_plain_text()

        # binary node
        if self._left_slot is None or self._right_slot is None:
            return ""

        return format_expr_str(
            self.SYMBOL,
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

    def dissolve(self) -> None:
        """Dissolve this node: serialize _left_slot, remove node, write text back."""
        from .widgets import ParenWidget

        parent = self.parent()
        if not isinstance(parent, ExpressionSlot):
            return

        left_text = self._left_slot.to_plain_text() if self._left_slot else ""
        parent.remove(self)

        focus = self._editor._last_focused
        if focus is None or not isinstance(focus, QLineEdit):
            focus = parent.default_input()
        cursor = focus.cursorPosition()
        focus.setText(focus.text()[:cursor] + left_text + focus.text()[cursor:])
        focus.setCursorPosition(cursor + len(left_text))

        # If parent slot is a ParenWidget with no inner nodes left, dissolve it too
        paren = parent.parent()
        if isinstance(paren, ParenWidget) and not any(
            isinstance(s, ExpressionNode) for s in parent._segments
        ):
            plain = paren.to_plain_text()
            paren._dissolve(False)
            target = self._editor._last_focused
            if target and isinstance(target, QLineEdit):
                cur = target.cursorPosition()
                target.setText(target.text()[:cur] + plain + target.text()[cur:])
                target.setCursorPosition(cur + len(left_text) + 1)

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
        editor: Expression,
        *,
        kind: InputKind,
        key: str,
        align: InputAlign,
        paren: tuple[str | None, str | None] | None = None,
    ) -> None:
        super().__init__(editor)

        self._editor = editor
        self._kind = kind
        self._key = key
        self._align = align
        self._paren = paren  # (open_symbol, close_symbol) or None
        self._segments: list[QWidget] = []
        self._direct_edits: list[QLineEdit] = []

        self.setProperty("exprSlot", True)
        self.setProperty("exprSlotKind", kind.value)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._layout = QHBoxLayout(self)

        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._layout.setAlignment(self._align.value)

        self.append_input()

        self._margin_scheduled = False
        self._on_node_removed: Callable[[], None] | None = None

    def _input_key(self) -> str:
        return f"{self._key}_{len(self._segments)}"

    def _run_autowidth(self, le: QLineEdit) -> None:
        try:
            le.setProperty("_aw_scheduled", False)
        except RuntimeError:
            return
        update_autowidth(le)

    def schedule_autowidth(self, le: QLineEdit) -> None:
        if self._editor._rendering:
            return
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
        le.setProperty("exprKind", self._kind.value)

        le.textChanged.connect(lambda _, seg=le: self._editor._on_input_changed(seg))
        le.textChanged.connect(lambda: self.schedule_autowidth(le))
        self._editor.input_created.emit(le)
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

    def serialize_segments(self, segs: list[QWidget]) -> str:
        """Return the plain-text representation of *segs*."""
        parts: list[str] = []
        for s in segs:
            if isinstance(s, QLineEdit):
                parts.append(s.text())
            elif isinstance(s, (ExpressionNode, ExpressionSlot)):
                parts.append(s.to_plain_text())
        return "".join(parts)

    def remove_segments(self, segs: list[QWidget]) -> None:
        """Remove a list of segments from this slot, destroying each widget."""
        for s in reversed(segs):
            if s not in self._segments:
                continue
            self._layout.removeWidget(s)
            self._segments.remove(s)
            if isinstance(s, QLineEdit) and s in self._direct_edits:
                self._direct_edits.remove(s)
            s.deleteLater()

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
            left.setText(left_text + right.text())
            self._layout.removeWidget(right)
            right.deleteLater()
            self._layout.removeWidget(seg)
            seg.deleteLater()
            self._direct_edits.remove(right)
            # update segments: remove right then node
            self._segments.pop(idx + 1)
            self._segments.pop(idx)
            left.setFocus()
            left.setCursorPosition(len(left_text))
            if self._on_node_removed:
                self._on_node_removed()
            return

        # fallback: simple removal
        self._layout.removeWidget(seg)
        seg.deleteLater()
        self._segments.remove(seg)

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
            if isinstance(seg, ExpressionNode):
                a = seg.anchor_y()
                b = seg.height() - a
            elif isinstance(seg, ExpressionSlot):
                a = seg.height() // 2
                b = seg.height() - a
            elif isinstance(seg, QLineEdit):
                a = seg.fontMetrics().height() // 2
                b = a
            else:
                continue
            if a > max_anchor:
                max_anchor = a
            if b > max_below:
                max_below = b

        for seg in self._segments:
            if isinstance(seg, ExpressionNode):
                own_anchor = seg.anchor_y()
                top = max(0, max_anchor - own_anchor)
                if seg.contentsMargins().top() != top:
                    seg.setContentsMargins(0, top, 0, 0)
            elif isinstance(seg, ExpressionSlot):
                own_anchor = seg.height() // 2
                top = max(0, max_anchor - own_anchor)
                if seg.contentsMargins().top() != top:
                    seg.setContentsMargins(0, top, 0, 0)
            elif isinstance(seg, QLineEdit):
                own_anchor = seg.fontMetrics().height() // 2
                top = max(0, max_anchor - own_anchor)
                if seg.textMargins().top() != top:
                    seg.setTextMargins(0, top, 0, 0)
            elif isinstance(seg, ParenGlyph):
                seg.setFixedHeight(max_anchor + max_below)

    def _schedule_margin_update(self) -> None:
        """Update margins after first frame render."""

        if self._margin_scheduled:
            return
        self._margin_scheduled = True
        QTimer.singleShot(0, self._do_margin_update)

    def _do_margin_update(self) -> None:
        self._margin_scheduled = False
        self._update_segment_margins()

        # Propagate margin child to parent
        node = self.parent()
        if isinstance(node, ExpressionNode):
            parent_slot = node.parent()
            if isinstance(parent_slot, ExpressionSlot):
                parent_slot._schedule_margin_update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._schedule_margin_update()
