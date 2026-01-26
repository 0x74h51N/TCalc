from __future__ import annotations

from enum import Enum
from typing import Optional

import calc_native
from PySide6.QtCore import Qt, QTimer, Signal
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

from tcalc.core.ops import Operation, get_symbols_with_aliases
from tcalc.ui.widgets.calc.config import display_config

from .utils import (
    CLOSE_KIND,
    OPEN_KIND,
    parenter,
    space_binary_ops,
    split_operand,
    split_paren,
    token_text,
    tokens_to_text,
    untokenized_prefix,
    update_autowidth,
    wrapped_in_parens,
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
            return tokens[1:-1] if wrapped_in_parens(tokens) else tokens

        self.left_tokens = strip_outer_parens(self.left_tokens)
        self.right_tokens = strip_outer_parens(self.right_tokens)

    OP_ID: calc_native.OpId | None = None

    def line_edits(self) -> list[QLineEdit]:
        return []

    def to_plain_text(self) -> str:
        return ""

    def focus_default(self) -> None:
        """Focus the default input after widget creation."""
        edits = self.line_edits()
        if edits:
            edits[-1].setFocus()

    def remove(self) -> None:
        """Remove this node from its parent slot."""
        parent = self.parent()
        if isinstance(parent, ExpressionSlot):
            parent.remove(self)
        else:
            self.deleteLater()


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

    OP_ID = calc_native.OpId.Div

    def __init__(
        self,
        editor: Expression,
        left_tokens: list[calc_native.Token] | None = None,
        right_tokens: list[calc_native.Token] | None = None,
    ) -> None:
        super().__init__(editor, left_tokens, right_tokens)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

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

        if self.left_tokens:
            self.numerator.default_input().setText(tokens_to_text(self.left_tokens))
        if self.right_tokens:
            self.denominator.default_input().setText(tokens_to_text(self.right_tokens))

    def line_edits(self) -> list[QLineEdit]:
        return [*self.numerator.line_edits(), *self.denominator.line_edits()]

    def focus_default(self) -> None:
        num_input = self.numerator.default_input()
        if not num_input.text():
            num_input.setFocus()
        else:
            self.denominator.default_input().setFocus()

    def to_plain_text(self) -> str:
        # TODO: tokens-first or cached structure
        # this setup does pointless text->token->text juggling and causes unnecessary conversions

        num_text = self.numerator.to_plain_text()
        den_text = self.denominator.to_plain_text()

        num_serial = parenter(calc_native.tokenize_string(num_text))
        den_serial = parenter(calc_native.tokenize_string(den_text))

        fraction_text = f"{num_serial}{Operation.DIV.symbol}{den_serial}"
        return parenter(fraction_text)


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

        if suffix_tokens:
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


# TODO: make proper test for this expressionist approach
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
