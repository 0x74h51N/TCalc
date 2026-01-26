from __future__ import annotations

import calc_native
from calc_native import tokenize_string
from PySide6.QtWidgets import QLineEdit

from tcalc.core.ops import OP_BY_ID, Operation
from tcalc.core.utils import is_number_token


def token_text(tok: calc_native.Token) -> str | int | float:
    if tok.kind == calc_native.TokenKind.Number:
        return tok.value
    if tok.kind == calc_native.TokenKind.Op:
        if tok.op_id == calc_native.OpId.Negate:
            return Operation.SUB.symbol
        return tok.symbol
    if tok.kind == calc_native.TokenKind.LParen:
        return Operation.OPEN_PAREN.symbol
    if tok.kind == calc_native.TokenKind.RParen:
        return Operation.CLOSE_PAREN.symbol
    return ""


def update_autowidth(le: QLineEdit) -> None:
    """Resize a QLineEdit to fit its current text length."""
    fm = le.fontMetrics()
    chars = max(1, len(le.text()))
    pad = fm.averageCharWidth()
    le.setFixedWidth(int(fm.averageCharWidth() * chars + pad))


def split_number(
    tokens: list[calc_native.Token], lead: bool = False
) -> tuple[list[calc_native.Token], list[calc_native.Token]]:
    """Split tokens at leading or trailing number. Returns (extracted, rest) if lead, else (rest, extracted)."""
    if not tokens:
        return ([], []) if lead else ([], [])
    if lead:
        if is_number_token(tokens[0]):
            return [tokens[0]], tokens[1:]
        return [], tokens
    else:
        if is_number_token(tokens[-1]):
            return tokens[:-1], [tokens[-1]]
        return tokens, []


def parenter(text: str) -> str:
    """Wrap expression in parentheses if it contains operator tokens."""
    if not text:
        return text
    toks = list(tokenize_string(text))
    if any(tok.kind == calc_native.TokenKind.Op for tok in toks):
        return f"({text})"
    return text


def space_binary_ops(parts: list[tuple[calc_native.OpId | None, str]]) -> str:
    """Insert spaces around binary operators (except division)."""
    out: list[str] = []
    for op_id, text in parts:
        if op_id is None:
            out.append(text)
            continue
        spec = OP_BY_ID[op_id]
        if spec.arity == calc_native.OpArity.Binary and op_id != calc_native.OpId.Div:
            out.append(f" {text} ")
        else:
            out.append(text)
    return "".join(out)


def tokens_to_text(tokens: list[calc_native.Token]) -> str:
    """Convert tokens to text with proper spacing for binary operators."""
    parts: list[tuple[calc_native.OpId | None, str]] = []
    for t in tokens:
        if t.kind == calc_native.TokenKind.Op:
            parts.append((t.op_id, str(token_text(t))))
        else:
            parts.append((None, str(token_text(t))))
    return space_binary_ops(parts)


def split_paren(
    tokens: list[calc_native.Token], lead: bool = False
) -> tuple[list[calc_native.Token], list[calc_native.Token]] | None:
    """Split tokens at leading or trailing '(...)' group. Returns (extracted, rest) if lead, else (rest, extracted)."""
    if not tokens:
        return None

    open_kind = calc_native.TokenKind.LParen
    close_kind = calc_native.TokenKind.RParen
    start_kind = open_kind if lead else close_kind

    if tokens[0 if lead else -1].kind != start_kind:
        return None

    depth = 0
    indices = range(len(tokens)) if lead else range(len(tokens) - 1, -1, -1)
    for i in indices:
        kind = tokens[i].kind
        if kind == open_kind:
            depth += 1 if lead else -1
        elif kind == close_kind:
            depth += -1 if lead else 1
        if depth == 0:
            split_at = i + 1 if lead else i
            return tokens[:split_at], tokens[split_at:]
    return None


def split_operand(
    tokens: list[calc_native.Token], lead: bool = False
) -> tuple[list[calc_native.Token], list[calc_native.Token]]:
    """Split tokens at leading or trailing operand (paren group or number). Returns (extracted, rest) if lead, else (rest, extracted)."""
    split = split_paren(tokens, lead)
    if split is not None:
        return split
    return split_number(tokens, lead)


def untokenized_prefix(text: str, tokens: list[calc_native.Token]) -> str:
    """Find text prefix that couldn't be tokenized (e.g. leading binary op like ' + ')."""
    if not tokens:
        return text

    first_tok = tokens[0]
    search_strs: list[str] = []

    if first_tok.kind == calc_native.TokenKind.Number:
        search_strs = [str(first_tok.value)]
    elif first_tok.kind == calc_native.TokenKind.Op:
        op = OP_BY_ID.get(first_tok.op_id)
        if op:
            search_strs = [op.symbol] + list(op.aliases or [])
    elif first_tok.kind == calc_native.TokenKind.LParen:
        search_strs = [Operation.OPEN_PAREN.symbol]
    elif first_tok.kind == calc_native.TokenKind.RParen:
        search_strs = [Operation.CLOSE_PAREN.symbol]

    for s in search_strs:
        idx = text.find(s)
        if idx >= 0:
            return text[:idx]
    return ""
