from __future__ import annotations

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


def space_binary_ops(op_id: calc_native.OpId | None, text: str) -> str:
    """Format a single operator with binary-op spacing if applicable (native)."""
    if op_id is None:
        return text
    return calc_native.space_binary_op(op_id, text)


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
