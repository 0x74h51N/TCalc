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
        return tok.symbol
    if tok.kind == OPEN_KIND:
        return OPEN_PAR
    if tok.kind == CLOSE_KIND:
        return CLOSE_PAR
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
        parts.append((t.op_id if t.kind == calc_native.TokenKind.Op else None, str(token_text(t))))

    return space_binary_ops(parts)


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
    """Split tokens at leading or trailing operand. Returns (extracted, rest) if lead, else (rest, extracted)."""
    split = split_paren(tokens, lead)
    if split is not None:
        return split
    return split_number(tokens, lead)


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
