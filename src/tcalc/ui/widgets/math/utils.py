#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

import calc_native
from PySide6.QtWidgets import QLineEdit

from tcalc.core.utils import is_number_token


def update_autowidth(le: QLineEdit) -> None:
    """Resize a QLineEdit to fit its current text length."""
    fm = le.fontMetrics()
    text_width = fm.horizontalAdvance(le.text())
    margins = le.textMargins()
    pad = margins.left() + margins.right() + fm.averageCharWidth()
    le.setFixedWidth(int(text_width + pad / 2))


@dataclass(kw_only=True)
class Split:
    idx: int
    prefix: list[calc_native.Token] = field(default_factory=list)
    left: list[calc_native.Token] = field(default_factory=list)
    right: list[calc_native.Token] = field(default_factory=list)
    suffix: list[calc_native.Token] = field(default_factory=list)


@dataclass
class ParenSplit(Split):
    open_tok: calc_native.ParenToken
    close_tok: calc_native.ParenToken | None

    @property
    def has_close(self) -> bool:
        return self.close_tok is not None


@dataclass
class ExprSplit(Split):
    kind: calc_native.ExprKind
    expr_tok: calc_native.ExprToken


StructuralSplit = Union[ParenSplit, ExprSplit]


def structural_split(
    tokens: list[calc_native.Token],
    classified: calc_native.TokenizeResult | None = None,
) -> StructuralSplit | None:
    """Find the next structural split point in *tokens*.

    Returns ParenSplit for an (un)matched open paren that appears before the
    first expression token, ExprSplit for Frac/Pow/Root/Log, or None when there
    are no expressions left to mount.
    """
    if not tokens:
        return None
    if classified is None:
        classified = calc_native.classify_tokens(tokens)
    if not classified.expr_indices:
        return None

    no_match = calc_native.PAREN_NO_MATCH
    expr_first = classified.expr_indices[0]

    candidate: int | None = None

    # Paren takes precedence when an open paren before the first expr token
    # is either unmatched or closes after that expr token, wrap the inner
    # tokens and let the caller re-enter structural_split on them.

    for ind in classified.open_paren_indices:
        if ind >= expr_first:
            continue
        pair = tokens[ind].as_paren().pair_idx
        if pair == no_match or pair > expr_first:
            candidate = ind
            break

    if candidate is not None:
        open_tok = tokens[candidate].as_paren()
        pair = open_tok.pair_idx
        has_close = pair != no_match
        close_tok = tokens[pair].as_paren() if has_close else None
        if has_close:
            inner = tokens[candidate + 1 : pair]
            suffix = tokens[pair + 1 :]
        else:
            inner = tokens[candidate + 1 :]
            suffix = []
        return ParenSplit(
            idx=candidate,
            open_tok=open_tok,
            close_tok=close_tok,
            prefix=tokens[:candidate],
            left=inner,
            suffix=suffix,
        )

    idx = expr_first
    expr_tok = tokens[idx].as_expr()
    before = tokens[:idx]
    after = tokens[idx + 1 :]

    if expr_tok.left:
        prefix = before
        left = list(expr_tok.left)
    else:
        prefix, left = split_operand(before)

    if expr_tok.right:
        right = list(expr_tok.right)
        suffix = after
    else:
        right, suffix = split_operand(after, lead=True, base_offset=idx + 1)

    return ExprSplit(
        idx=idx,
        kind=expr_tok.kind,
        expr_tok=expr_tok,
        prefix=prefix,
        left=left,
        right=right,
        suffix=suffix,
    )


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
