from __future__ import annotations

from enum import Enum
from typing import Optional

import calc_native
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.ops import OP_BY_ID, Operation, get_symbols_with_aliases
from tcalc.ui.widgets.calc.config import display_config

from .utils import (
    parenter,
    space_binary_ops,
    split_outer_paren_tail,
    split_trailing_number,
    token_text,
    update_autowidth,
)


class InputKind(Enum):
    """Tag inputs as main expression or auxiliary slots."""

    MAIN = "main"
    AUX = "aux"


class InputAlign(Enum):
    """Predefined alignment flags for expression inputs."""

    LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    CENTER = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
    RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


class ExpressionNode(QWidget):
    """Base class for math expression widgets that can serialize to text."""

    def line_edits(self) -> list[QLineEdit]:
        return []

    def to_plain_text(self) -> str:
        return ""

    def remove(self) -> None:
        """Remove this node from its parent slot."""
        parent = self.parent()
        if isinstance(parent, ExpressionSlot):
            parent.remove(self)
        else:
            self.deleteLater()

    def apply_carry_from(self, text: str) -> tuple[str, int]:
        """Split trailing number from text and apply it to the first input."""
        trimmed = text.rstrip()
        split = split_outer_paren_tail(list(trimmed))
        if split is not None:
            prefix, carry = ("".join(part) for part in split)
            edits = self.line_edits()
            if edits:
                edits[0].setText(carry)
                return prefix, -1
            return prefix, 0

        prefix, carry = split_trailing_number(trimmed)
        edits = self.line_edits()
        if carry and edits:
            edits[0].setText(carry)
            return prefix, -1
        return prefix, 0


class ExpressionSlot(QWidget):
    """A horizontal slot that holds inputs and nested expression nodes."""

    def __init__(self, editor: Expression, *, kind: InputKind, key: str, align: InputAlign) -> None:
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

    def append_input(self) -> QLineEdit:
        le = self._editor._create_input(
            self._input_key(), kind=self._kind, align=self._align, parent=self
        )
        self._layout.addWidget(le, 0, self._align.value)
        self._segments.append(le)
        return le

    def insert_widget(self, index: int, w: QWidget) -> None:
        self._layout.insertWidget(index, w, 0, self._align.value)
        self._segments.insert(index, w)

    def default_input(self) -> QLineEdit:
        for seg in reversed(self._segments):
            if isinstance(seg, QLineEdit):
                return seg
        return self.append_input()

    def index_of(self, seg: QWidget) -> int:
        return self._segments.index(seg)

    def remove(self, seg: QWidget) -> None:
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


class FractionWidget(ExpressionNode):
    """UI node for a fraction with numerator and denominator slots."""

    def __init__(self, editor: "Expression", op: Operation) -> None:
        super().__init__(editor)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self._op = op

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.numerator = ExpressionSlot(
            editor, kind=InputKind.AUX, key="numerator", align=InputAlign.CENTER
        )
        layout.addWidget(self.numerator, 0, Qt.AlignmentFlag.AlignHCenter)

        line = QFrame(self)
        line.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        line.setMinimumWidth(0)
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        self.denominator = ExpressionSlot(
            editor, kind=InputKind.AUX, key="denominator", align=InputAlign.CENTER
        )
        layout.addWidget(self.denominator, 0, Qt.AlignmentFlag.AlignHCenter)

    def line_edits(self) -> list[QLineEdit]:
        return [*self.numerator.line_edits(), *self.denominator.line_edits()]

    def to_plain_text(self) -> str:
        op_symbol = self._op.symbol
        numerator = parenter(self.numerator.to_plain_text())
        denominator = parenter(self.denominator.to_plain_text())
        return f"({numerator}{op_symbol}{denominator})"


class Expression(QWidget):
    """Expression editor widget managing inputs and serialization for math-style UI."""

    plain_text_changed = Signal(str)

    EXPR_PREFIX = "displayExpression_"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._last_focused: QLineEdit | None = None

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
        update_autowidth(le)
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
        self.plain_text_changed.emit(self.get_plain_text())

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
        if target.hasSelectedText() or target.cursorPosition() > 0:
            target.backspace()
            return

        slot = target.parent()
        if not isinstance(slot, ExpressionSlot):
            target.backspace()
            return

        idx = slot.index_of(target)
        if not target.text() and idx > 0:
            prev = slot._segments[idx - 1]
            if isinstance(prev, ExpressionNode):
                prev.remove()
                self.plain_text_changed.emit(self.get_plain_text())
                return
            if isinstance(prev, QLineEdit):
                self._focus_backspace(prev)
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

        paren_split = split_outer_paren_tail([part[1] for part in parts])
        paren_start = len(paren_split[0]) if paren_split else None
        for i in range(len(parts) - 1, -1, -1):
            op_id = parts[i][0]
            txt = parts[i][1]
            if i == len(parts) - 1 and (
                txt == Operation.OPEN_PAREN.symbol
                or (op_id is not None and OP_BY_ID[op_id].arity == calc_native.OpArity.Binary)
            ):
                if op_id == calc_native.OpId.Negate:
                    parts.pop(i)
                else:
                    parts.insert(i + 1, (calc_native.OpId.Negate, Operation.SUB.symbol))
                apply_prefix(space_binary_ops(parts))
                return
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
        """Insert operator text or create a fraction widget for division."""

        if op.symbol == Operation.DIV.symbol:
            target = self._resolve_target()
            slot = target.parent()
            assert isinstance(slot, ExpressionSlot)
            self._insert_node(target, slot, FractionWidget(self, op))
            return

        if op.arity == calc_native.OpArity.Unary:
            self.insert_text(f"{label}{Operation.OPEN_PAREN.symbol}")
            return

        op_id = getattr(op._spec, "id", None)
        self.insert_text(space_binary_ops([(op_id, label)]))

    def _focus_backspace(self, le: QLineEdit) -> None:
        le.setFocus()
        le.setCursorPosition(len(le.text()))
        le.backspace()

    def _insert_node(self, target: QLineEdit, slot: ExpressionSlot, node: ExpressionNode) -> None:
        """Insert a math expression node after target, carrying trailing numbers."""
        prefix, focus_idx = node.apply_carry_from(target.text())
        if prefix != target.text():
            target.setText(prefix)
        idx = slot.index_of(target)
        slot.insert_widget(idx + 1, node)
        if idx + 1 == (len(slot._segments) - 1):
            slot.append_input()
        edits = node.line_edits()
        if edits:
            edits[focus_idx].setFocus()
        self.plain_text_changed.emit(self.get_plain_text())
