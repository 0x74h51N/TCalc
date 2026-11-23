#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""probe layers: one case on each layer, in the order docs/rules/ai/tests.md asks for."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import calc_native

from probes.grade import finish
from probes.options import Input, Options, read_inputs
from probes.rows import (
    Layer,
    ProbeError,
    Row,
    error_row,
    format_rows,
    operand_input,
    probe_error_row,
    text_row,
    value_row,
)
from tcalc.core.ops import OP_BY_ID
from tcalc.core.utils import CalcValue
from tcalc.ui.controller.utils import format_result

# the native core's errors, and a RuntimeError it lets through (seen: `1,2`, Boost's "non-numeric content")
NATIVE_ERRORS = (calc_native.CalculatorError, RuntimeError)
Token = calc_native.Token
TokenKind = calc_native.TokenKind


_OP_IDS: dict[TokenKind, Callable[[Token], calc_native.OpId]] = {
    TokenKind.Op: lambda t: t.as_op().op_id,
    TokenKind.Call: lambda t: t.as_call().op_id,
    TokenKind.Latex: lambda t: t.as_latex().op_id,
}


def _op_name(token: Token) -> str:
    """The op id a token carries, so two forms of one op can be told apart (⌄ and \\root are both Root)."""
    read = _OP_IDS.get(token.kind)
    op = read(token) if read is not None else None
    # a Subscript, Sum or Prod LaTeX token carries no op of its own
    return f":{op.name}" if op is not None and op in OP_BY_ID else ""


def _tokens_text(tokens: Sequence[Token]) -> str:
    return "  ".join(f"{t.kind.name}:{calc_native.token_text(t)}{_op_name(t)}" for t in tokens)


def _flat(tokens: Sequence[Token]) -> str:
    return " ".join(calc_native.token_text(t) for t in tokens)


def _split_text(branch: calc_native.TokensBranch) -> str:
    split = calc_native.structural_split(branch)
    if isinstance(split, calc_native.LatexSplit):
        return f"{split.kind.name}  left {_flat(split.left)}  right {_flat(split.right)}"
    if isinstance(split, calc_native.ParenSplit):
        return f"paren of {len(split.elements)} elements"
    return "none"


def _evaluate(branch: calc_native.TokensBranch, unit: calc_native.AngleUnit) -> CalcValue:
    """The binding alone on a clean variable store, as eval does, so no input sees another's A=."""
    calc_native.clear_vars()
    return calc_native.evaluate(branch, calc_native.Calculator(), unit)


def _op_alone_rows(
    text: str, branch: calc_native.TokensBranch, unit: calc_native.AngleUnit
) -> list[Row]:
    """The op the row applies last, alone through apply, on the operands the evaluator hands it."""
    try:
        calc_native.clear_vars()
        root = calc_native.root_operands(branch, calc_native.Calculator(), unit)
    except NATIVE_ERRORS:
        # the operands fail as the binding does, and its row already shows that error
        return []
    if root is None:
        return []
    op, operands = root
    alone = operand_input(OP_BY_ID[op].symbol, operands)
    try:
        value = calc_native.apply(calc_native.Calculator(), op, operands, unit)
    except NATIVE_ERRORS as error:
        return [error_row(alone, Layer.APPLY, error, unit)]
    return [
        value_row(alone, Layer.APPLY, value, unit),
        text_row(alone, Layer.WRITTEN, format_result(value)),
    ]


def layer_rows(text: str, unit: calc_native.AngleUnit) -> list[Row]:
    branch = calc_native.tokenize_string(text)
    tokens = branch.tokens
    rows = [
        text_row(text, Layer.TOKENS, _tokens_text(tokens)),
        text_row(text, Layer.FLAT, calc_native.tokens_to_flat_text(tokens)),
        text_row(text, Layer.RPN, _flat(calc_native.shunting_yard(tokens))),
    ]
    if any(t.kind == TokenKind.Latex for t in tokens):
        rows += [
            text_row(text, Layer.NODES, str(calc_native.build_math_nodes(branch))),
            text_row(text, Layer.SPLIT, _split_text(branch)),
        ]
    try:
        value = _evaluate(branch, unit)
    except NATIVE_ERRORS as error:
        binding = [error_row(text, Layer.BINDING, error, unit)]
    else:
        binding = [
            value_row(text, Layer.BINDING, value, unit),
            text_row(text, Layer.WRITTEN, format_result(value)),
        ]
    # the op alone is worth most when the binding fails, so it is shown either way
    return [*rows, *binding, *_op_alone_rows(text, branch, unit)]


def _input_rows(one: Input, options: Options) -> list[Row]:
    try:
        return finish(layer_rows(one.text, options.unit), one.beside, options.ref)
    except ProbeError as error:
        return [probe_error_row(one.text, error)]


def run(options: Options) -> int:
    rows = [row for one in read_inputs(options) for row in _input_rows(one, options)]
    print(format_rows(rows), end="")
    return 0
