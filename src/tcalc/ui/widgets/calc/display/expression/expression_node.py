from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, ClassVar

import calc_native
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QWidget,
)

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


class ExpressionNode(QWidget):
    """Base class for math expression widgets that can serialize to text."""

    def __init__(
        self,
        editor: Expression,
        left_tokens: list[calc_native.Token] | None,
        right_tokens: list[calc_native.Token] | None,
    ):
        super().__init__(editor)
        self.left_tokens = left_tokens if left_tokens is not None else []
        self.right_tokens = right_tokens if right_tokens is not None else []

        def strip_outer_parens(tokens):
            return tokens

        self.left_tokens = strip_outer_parens(self.left_tokens)
        self.right_tokens = strip_outer_parens(self.right_tokens)

        self._left_slot: ExpressionSlot | None = None
        self._right_slot: ExpressionSlot | None = None
        self._top_slot: ExpressionSlot | None = None
        self._bottom_slot: ExpressionSlot | None = None

    OP_ID: ClassVar[calc_native.OpId]
    EXPR_KIND: ClassVar[calc_native.ExprKind]
    SYMBOL: ClassVar[str]

    def line_edits(self) -> list[QLineEdit]:
        out = []
        if self._left_slot:
            out.extend(self._left_slot.line_edits())
        if self._right_slot:
            out.extend(self._right_slot.line_edits())
        return out

    def to_plain_text(self) -> str:
        """Serialize to LaTeX-style format: \\symbol{left}{right}."""
        if self._left_slot is None or self._right_slot is None:
            return ""
        return format_expr_str(
            self.SYMBOL, self._left_slot.to_plain_text(), self._right_slot.to_plain_text()
        )

    def focus_default(self) -> None:
        """Focus the default input after widget creation."""
        edits = self.line_edits()
        if edits:
            edits[-1].setFocus()

    def slot_above(self, current: ExpressionSlot) -> ExpressionSlot | None:
        return self._top_slot if current is self._bottom_slot else None

    def slot_below(self, current: ExpressionSlot) -> ExpressionSlot | None:
        return self._bottom_slot if current is self._top_slot else None

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
    ) -> None:
        super().__init__(editor)

        self._editor = editor
        self._kind = kind
        self._key = key
        self._align = align
        self._segments: list[QWidget] = []

        self.setProperty("exprSlot", True)
        self.setProperty("exprSlotKind", kind.value)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._layout = QHBoxLayout(self)

        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._layout.setAlignment(self._align.value)

        self.append_input()

    def _input_key(self) -> str:
        return f"{self._key}_{len(self._segments)}"

    def _run_autowidth(self, le: QLineEdit) -> None:
        le.setProperty("_aw_scheduled", False)
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
        return le

    def insert_widget(self, index: int, w: QWidget) -> None:
        self._layout.insertWidget(index, w, 0, self._align.value)
        self._segments.insert(index, w)

    def insert_input(self, index: int) -> QLineEdit:
        le = self._create_input(self._input_key())
        self._layout.insertWidget(index, le, 0, self._align.value)
        self._segments.insert(index, le)
        return le

    def default_input(self) -> QLineEdit:
        for seg in reversed(self._segments):
            if isinstance(seg, QLineEdit):
                return seg
        return self.append_input()

    def index_of(self, seg: QWidget) -> int:
        return self._segments.index(seg)

    def remove(self, seg: QWidget) -> None:
        if seg not in self._segments:
            return

        idx = self._segments.index(seg)

        # If node with QLineEdit neighbors, merge them into one and remove node+right
        left = self._segments[idx - 1]
        right = self._segments[idx + 1]
        if isinstance(left, QLineEdit) and isinstance(right, QLineEdit):
            left_text = left.text()
            left.setText(left_text + right.text())
            self._layout.removeWidget(right)
            right.deleteLater()
            self._layout.removeWidget(seg)
            seg.deleteLater()
            # update segments: remove right then node
            self._segments.pop(idx + 1)
            self._segments.pop(idx)
            left.setFocus()
            left.setCursorPosition(len(left_text))
            return

        # fallback: simple removal
        self._layout.removeWidget(seg)
        seg.deleteLater()
        self._segments.remove(seg)

    def reset(self) -> QLineEdit:
        for seg in self._segments:
            self._layout.removeWidget(seg)
            seg.deleteLater()
        self._segments = []

        return self.append_input()

    def line_edits(self) -> list[QLineEdit]:
        out: list[QLineEdit] = []
        for seg in self._segments:
            if isinstance(seg, QLineEdit):
                out.append(seg)
                continue
            if isinstance(seg, ExpressionNode):
                out.extend(seg.line_edits())
        return out

    def to_plain_text(self) -> str:
        parts: list[str] = []
        for seg in self._segments:
            if isinstance(seg, QLineEdit):
                parts.append(seg.text())
                continue
            if isinstance(seg, ExpressionNode):
                parts.append(seg.to_plain_text())
        return "".join(parts)


# TODO: Fix the alignment issue about main ExpressionSlot and so on...
