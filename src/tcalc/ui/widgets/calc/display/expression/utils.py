from __future__ import annotations

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


def split_operand(
    tokens: list[calc_native.Token], lead: bool = False, base_offset: int = 0
) -> tuple[list[calc_native.Token], list[calc_native.Token]]:
    """Extract leading/trailing operand from tokens.

    base_offset: index offset of tokens[0] in the original token list.
    Used to convert pair_idx (absolute) to a local index within this slice.
    """
    if not tokens:
        return [], []

    no_match = calc_native.PAREN_NO_MATCH

    if lead:
        first = tokens[0]
        # (...) - paren group
        if (
            isinstance(first.data, calc_native.ParenToken)
            and first.data.type == calc_native.ParenType.Open
        ):
            pair = first.data.pair_idx
            if pair != no_match:
                local_end = pair - base_offset + 1
            else:
                local_end = len(tokens)
            operand = tokens[:local_end]
            suffix = tokens[local_end:]
            return operand, suffix

        if is_number_token(first):
            return [first], tokens[1:]

        return [], tokens

    # trailing (lead=False)
    last = tokens[-1]

    # (...) - paren group -> (3+4)/
    if (
        isinstance(last.data, calc_native.ParenToken)
        and last.data.type == calc_native.ParenType.Close
    ):
        pair = last.data.pair_idx
        if pair != no_match:
            local_start = pair - base_offset
        else:
            local_start = 0
        operand = tokens[local_start:]
        prefix = tokens[:local_start]
        return prefix, operand

    if is_number_token(last):
        return tokens[:-1], [last]

    return tokens, []
