from __future__ import annotations

import calc_native
from calc_native import tokenize_string
from PySide6.QtWidgets import QLineEdit

from tcalc.core.ops import OP_BY_ID, Operation
from tcalc.core.utils import is_number_token

OPEN_PAR = Operation.OPEN_PAREN.symbol
CLOSE_PAR = Operation.CLOSE_PAREN.symbol
OPEN_KIND = calc_native.TokenKind.LParen
CLOSE_KIND = calc_native.TokenKind.RParen


def token_text(tok: calc_native.Token) -> str | int | float:
    if tok.kind == calc_native.TokenKind.Number:
        return tok.value
    if tok.kind == calc_native.TokenKind.Op:
        if tok.op_id == calc_native.OpId.Negate:
            return Operation.SUB.symbol
        if tok.op_id == calc_native.OpId.UnaryPlus:
            return Operation.ADD.symbol
        return tok.symbol
    if tok.kind == OPEN_KIND:
        return OPEN_PAR
    if tok.kind == CLOSE_KIND:
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


def parenter(text_or_tokens: str | list[calc_native.Token]) -> str:
    """Wrap expression in parentheses if it contains ops and don't wrapped parentheses."""
    if isinstance(text_or_tokens, list):
        toks = text_or_tokens
        if not toks:
            return ""
        if wrapped_in_parens(toks):
            return tokens_to_text(toks)
        if any(tok.kind == calc_native.TokenKind.Op for tok in toks):
            return f"{OPEN_PAR}{tokens_to_text(toks)}{CLOSE_PAR}"
        return tokens_to_text(toks)

    text = text_or_tokens
    toks = list(tokenize_string(text))
    return parenter(toks)


def _get_visual_node_ops() -> set[calc_native.OpId]:
    """Lazy import to avoid circular dependency."""
    from .expression import Expression

    return set(Expression.NODE_WIDGETS.keys())


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


def untokenized_prefix(text: str, tokens: list[calc_native.Token]) -> str:
    """Return untokenized prefix."""
    if not tokens:
        return text
    first_tok = tokens[0]

    idx = text.find(str(token_text(first_tok)))
    if idx >= 0:
        return text[:idx]
    return ""


def wrapped_in_parens(tokens: list[calc_native.Token]) -> bool:
    if not tokens:
        return False
    if tokens[0].kind != OPEN_KIND or tokens[-1].kind != CLOSE_KIND:
        return False

    depth = 0
    for i, t in enumerate(tokens):
        if t.kind == OPEN_KIND:
            depth += 1
        elif t.kind == CLOSE_KIND:
            depth -= 1
        if depth == 0:
            return i == len(tokens) - 1

    return False
