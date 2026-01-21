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


def split_trailing_number(text: str) -> tuple[str, str]:
    """Split text into prefix and trailing numeric token (if present)."""
    toks = list(tokenize_string(text)) if text else []
    if not toks or not is_number_token(toks[-1]):
        return text, ""
    carry = str(token_text(toks[-1]))
    if carry and text.endswith(carry):
        return text[: -len(carry)], carry
    return text, ""


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
