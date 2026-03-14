from __future__ import annotations

import calc_native


def space_binary_ops(op_id: calc_native.OpId | None, text: str) -> str:
    """Format a single operator with binary-op spacing if applicable (native)."""
    if op_id is None:
        return text
    return calc_native.space_binary_op(op_id, text)
