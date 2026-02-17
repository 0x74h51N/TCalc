from __future__ import annotations

from collections import defaultdict

import calc_native
from PySide6.QtWidgets import QLineEdit

from tcalc.core.ops import OP_BY_ID, LatexExpr, Operation
from tcalc.core.utils import is_number_token

UNARY_OP_SYMBOL_MAP: dict[calc_native.OpId, str] = {
    calc_native.OpId.Negate: Operation.SUB.symbol,
    calc_native.OpId.UnaryPlus: Operation.ADD.symbol,
}
VISUAL_NODE_OPS: set[calc_native.OpId] | None = None


def format_expr_str(symbol: str, left: str, right: str) -> str:
    """Format LaTeX-style expression: \\symbol{left}{right}."""
    return f"{symbol}{{{left}}}{{{right}}}"


def token_text(tok: calc_native.Token) -> str:
    """Convert a single token to its text representation."""
    match tok.data:
        case calc_native.ExprToken():
            symbol = LatexExpr.get(tok.data.kind).symbol
            return format_expr_str(
                symbol, tokens_to_text(tok.data.left), tokens_to_text(tok.data.right)
            )
        case calc_native.NumberToken():
            return tok.data.value
        case calc_native.OpToken():
            return UNARY_OP_SYMBOL_MAP.get(tok.data.op_id, tok.symbol)
        case calc_native.ParenToken():
            return tok.data.symbol

    return ""


def tokens_to_text(tokens: list[calc_native.Token]) -> str:
    """Convert tokens to text with proper spacing for binary operators."""
    parts: list[tuple[calc_native.OpId | None, str]] = []

    for t in tokens:
        parts.append(
            (t.data.op_id if isinstance(t.data, calc_native.OpToken) else None, str(token_text(t)))
        )

    return space_binary_ops(parts)


def update_autowidth(le: QLineEdit) -> None:
    """Resize a QLineEdit to fit its current text length."""
    fm = le.fontMetrics()
    text_width = fm.horizontalAdvance(le.text())
    margins = le.textMargins()
    pad = margins.left() + margins.right() + fm.averageCharWidth()
    le.setFixedWidth(int(text_width + pad / 2))


def _get_visual_node_ops() -> set[calc_native.OpId]:
    global VISUAL_NODE_OPS
    if VISUAL_NODE_OPS is None:
        from .expression import Expression

        VISUAL_NODE_OPS = {cls.OP_ID for cls in Expression.EXPR_KIND_MAP.values()}
    return VISUAL_NODE_OPS


def space_binary_ops(parts: list[tuple[calc_native.OpId | None, str]]) -> str:
    """Insert spaces around binary operators - except ExpressionNode visualisated ops."""
    visual_ops = _get_visual_node_ops()
    out: list[str] = []
    for op_id, text in parts:
        if op_id is None:
            out.append(text)
            continue
        spec = OP_BY_ID[op_id]
        if spec.arity == calc_native.OpArity.Binary and op_id not in visual_ops:
            out.append(f" {text} ")
        else:
            out.append(text)
    return "".join(out)


def split_paren(tokens: list[calc_native.Token], lead: bool = True):
    """Split tokens at a balanced paren group (matching ParenKind), tracking all types."""

    if not tokens:
        return None

    indices = range(len(tokens)) if lead else range(len(tokens) - 1, -1, -1)

    depths: dict[calc_native.ParenKind, int] = defaultdict(int)
    opening_index: int | None = None
    opening_kind: calc_native.ParenKind | None = None

    for i in indices:
        tok = tokens[i]
        if tok.kind != calc_native.TokenKind.Paren:
            continue
        if not isinstance(tok.data, calc_native.ParenToken):
            continue

        ptype = tok.data.type
        pkind = tok.data.kind

        if sum(depths.values()) == 0 and ptype == calc_native.ParenType.Open:
            opening_index = i
            opening_kind = pkind

        if ptype == calc_native.ParenType.Open:
            depths[pkind] += 1
        elif ptype == calc_native.ParenType.Close:
            depths[pkind] -= 1

        if opening_index is not None and opening_kind is not None and depths[opening_kind] == 0:
            split_at = i + 1 if lead else i
            return tokens[opening_index:split_at], tokens[:opening_index] + tokens[split_at:]

    return None


def split_operand(
    tokens: list[calc_native.Token], lead: bool = False
) -> tuple[list[calc_native.Token], list[calc_native.Token]]:
    """Extract leading/trailing operand from tokens."""
    if not tokens:
        return [], []

    if lead:
        first = tokens[0]
        # (...) - paren group
        if (
            isinstance(first.data, calc_native.ParenToken)
            and first.data.type == calc_native.ParenType.Open
        ):
            paren_split = split_paren(tokens, lead=True)
            if paren_split:
                return paren_split

        if is_number_token(first):
            return [first], tokens[1:]

        return [], tokens

    # trailing (lead=False)
    last = tokens[-1]

    # # (...) - paren group -> (3+4)/
    if (
        isinstance(last.data, calc_native.ParenToken)
        and last.data.type == calc_native.ParenType.Close
    ):
        paren_split = split_paren(tokens, lead=False)
        if paren_split:
            return paren_split

    if is_number_token(last):
        return tokens[:-1], [last]

    return tokens, []
