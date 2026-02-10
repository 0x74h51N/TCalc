from __future__ import annotations

import calc_native
from PySide6.QtWidgets import QLineEdit

from tcalc.core.ops import OP_BY_ID, LatexExpr, Operation
from tcalc.core.utils import is_number_token

OPEN_PAR = Operation.OPEN_PAREN.symbol
CLOSE_PAR = Operation.CLOSE_PAREN.symbol
OPEN_KIND = calc_native.TokenKind.LParen
CLOSE_KIND = calc_native.TokenKind.RParen

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
    match tok.kind:
        case calc_native.TokenKind.Expr:
            symbol = LatexExpr.get(tok.expr_kind).symbol
            return format_expr_str(
                symbol, tokens_to_text(tok.left_tokens), tokens_to_text(tok.right_tokens)
            )
        case calc_native.TokenKind.Number:
            return tok.value
        case calc_native.TokenKind.Op:
            return UNARY_OP_SYMBOL_MAP.get(tok.op_id, tok.symbol)
        case calc_native.TokenKind.LParen:
            return OPEN_PAR
        case calc_native.TokenKind.RParen:
            return CLOSE_PAR
    return ""


def tokens_to_text(tokens: list[calc_native.Token]) -> str:
    """Convert tokens to text with proper spacing for binary operators."""
    parts: list[tuple[calc_native.OpId | None, str]] = []

    for t in tokens:
        parts.append((t.op_id if t.kind == calc_native.TokenKind.Op else None, str(token_text(t))))

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


def split_paren(
    tokens: list[calc_native.Token], lead: bool = False
) -> tuple[list[calc_native.Token], list[calc_native.Token]] | None:
    """Split tokens at leading or trailing '(...)' group. Returns (extracted, rest) if lead, else (rest, extracted)."""

    depth = 0
    indices = range(len(tokens)) if lead else range(len(tokens) - 1, -1, -1)
    for i in indices:
        kind = tokens[i].kind
        if kind == OPEN_KIND:
            depth += 1 if lead else -1
        elif kind == CLOSE_KIND:
            depth += -1 if lead else 1
        if depth == 0:
            split_at = i + 1 if lead else i
            return tokens[:split_at], tokens[split_at:]
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
        if first.kind == OPEN_KIND:
            paren_split = split_paren(tokens, lead=True)
            if paren_split:
                return paren_split

        if is_number_token(first):
            return [first], tokens[1:]

        return [], tokens

    # trailing (lead=False)
    last = tokens[-1]

    # # (...) - paren group -> (3+4)/
    if last.kind == CLOSE_KIND:
        paren_split = split_paren(tokens, lead=False)
        if paren_split:
            return paren_split

    if is_number_token(last):
        return tokens[:-1], [last]

    return tokens, []
