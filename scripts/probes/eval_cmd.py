#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""probe eval: a case through the whole Python path, as the app evaluates it."""

from __future__ import annotations

import calc_native

from probes.app import offscreen_app
from probes.grade import finish
from probes.options import Input, Options, read_inputs
from probes.rows import (
    Layer,
    ProbeError,
    Row,
    error_row,
    exact_text,
    format_rows,
    probe_error_row,
    text_row,
    type_name,
    value_row,
)
from tcalc.core.native_eval import evaluate_branch
from tcalc.core.parser import tokenize
from tcalc.core.utils import CalcValue
from tcalc.errors import CalculatorError
from tcalc.ui.controller.utils import format_result
from tcalc.ui.widgets.calc.display.expression.expression import Expression

SAME = "same"
# what the controller catches around an evaluation: TCalc's errors, and a RuntimeError the
# native core lets through (seen: `$` raises Boost's "non-numeric content")
EVAL_ERRORS = (CalculatorError, RuntimeError)


def _editor_text(editor: Expression, text: str) -> str:
    """What the editor makes of the text: the text the controller evaluates."""
    editor.set_plain_text(text)
    offscreen_app().processEvents()
    return editor.get_plain_text()


def _evaluate(text: str, unit: calc_native.AngleUnit) -> CalcValue:
    calc_native.clear_vars()
    return evaluate_branch(tokenize(text), calc_native.Calculator(), unit)


def _round_trip(value: CalcValue, written: str, unit: calc_native.AngleUnit) -> str:
    # == on a bound type compares identity, so the type and the exact text are compared
    try:
        again = _evaluate(written, unit)
    except EVAL_ERRORS as error:
        return f"{type_name(error)} {error}"
    same = type(again) is type(value) and exact_text(again) == exact_text(value)
    return SAME if same else f"{type_name(again)} {exact_text(again)}"


def eval_rows(editor: Expression, text: str, unit: calc_native.AngleUnit) -> list[Row]:
    canonical = _editor_text(editor, text)
    rows = [text_row(text, Layer.EDITOR, canonical)]
    try:
        value = _evaluate(canonical, unit)
    except EVAL_ERRORS as error:
        return [*rows, error_row(canonical, Layer.EVAL, error, unit)]
    written = format_result(value)
    return [
        *rows,
        value_row(canonical, Layer.EVAL, value, unit),
        text_row(canonical, Layer.DISPLAY, format_result(value, group=True)),
        text_row(canonical, Layer.WRITTEN, written),
        text_row(written, Layer.ROUND_TRIP, _round_trip(value, written, unit)),
    ]


def _input_rows(editor: Expression, one: Input, options: Options) -> list[Row]:
    try:
        return finish(eval_rows(editor, one.text, options.unit), one.beside, options.ref)
    except ProbeError as error:
        return [probe_error_row(one.text, error)]


def run(options: Options) -> int:
    offscreen_app()
    editor = Expression()
    rows = [row for one in read_inputs(options) for row in _input_rows(editor, one, options)]
    print(format_rows(rows), end="")
    return 0
